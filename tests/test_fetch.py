"""Sobriété des appels sortants : cache partagé, single-flight, secours, nouvel essai,
budget. Aucun accès réseau : urlopen est remplacé par un faux qui compte les appels.
Lancer : python -m pytest"""
import datetime as dt
import http.client
import io
import json
import os
import sys
import threading
import time
import unittest
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import server  # noqa: E402
from app import fetch, sources  # noqa: E402


def fake_hourly(url):
    """Réponse Open-Meteo plausible : 7 jours passés + 3 de prévision, valeurs constantes."""
    start = dt.date.today() - dt.timedelta(days=sources.FETCH_PAST_DAYS)
    times = [f"{start + dt.timedelta(days=d)}T{h:02d}:00"
             for d in range(sources.FETCH_PAST_DAYS + sources.FORECAST_DAYS) for h in range(24)]
    names = sources.MARINE_VARS if "marine" in url else sources.WIND_VARS
    vals = {"wave_height": 1.2, "wave_period": 10, "swell_wave_height": 1.0,
            "swell_wave_peak_period": 11, "wind_speed_10m": 8, "sea_surface_temperature": 16,
            "temperature_2m": 18, "apparent_temperature": 17}
    hourly = {"time": times}
    for n in names:
        if n == "sea_level_height_msl":
            hourly[n] = [round(2 * __import__("math").sin(i / 2), 2) for i in range(len(times))]
        else:
            hourly[n] = [vals.get(n, 270 if "direction" in n else 0.5)] * len(times)
    return {"hourly": hourly}


class FakeUpstream:
    """Remplace fetch._urlopen ; compte les appels, peut être lent ou en panne."""

    def __init__(self, delay=0.0, fail=0, status=None):
        self.calls, self.delay, self.fail, self.status = [], delay, fail, status
        self.lock = threading.Lock()

    def __call__(self, req, timeout):
        with self.lock:
            self.calls.append(req.full_url)
            n = len(self.calls)
        time.sleep(self.delay)
        if n <= self.fail:
            if self.status:
                raise urllib.error.HTTPError(req.full_url, self.status, "x", {}, None)
            raise urllib.error.URLError("panne simulée")
        return io.BytesIO(json.dumps(fake_hourly(req.full_url)).encode())


class Base(unittest.TestCase):
    def setUp(self):
        self.cache = fetch.Cache(None)          # mémoire seule, isolée
        self.patches = [
            mock.patch.object(sources, "CACHE", self.cache),
            mock.patch.object(fetch, "BUDGET", fetch.DailyBudget(fetch.DAILY_BUDGET)),
            mock.patch.object(fetch, "LIMITER", fetch.RateLimiter(rate=1000, burst=1000)),
            mock.patch.object(fetch, "_sleep", lambda s: None),   # pas d'attente de backoff
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()


class CacheTests(Base):
    def test_single_flight(self):
        """N demandes simultanées de la même clé -> UN seul appel à la source."""
        calls = []

        def slow():
            calls.append(1)
            time.sleep(0.3)
            return {"ok": True}

        with ThreadPoolExecutor(50) as ex:
            res = list(ex.map(lambda _: self.cache.get("k", 60, slow), range(50)))
        self.assertEqual(len(calls), 1)
        self.assertTrue(all(r == {"ok": True} for r in res))

    def test_fresh_hit_no_call(self):
        n = []
        self.cache.get("k", 60, lambda: n.append(1) or 1)
        self.cache.get("k", 60, lambda: n.append(1) or 2)
        self.assertEqual(len(n), 1)

    def test_stale_on_error(self):
        self.cache.get("k", 60, lambda: "ancien")
        t, v = self.cache.mem["k"]
        self.cache.mem["k"] = (t - 3600, v)          # périmé
        self.assertEqual(self.cache.get("k", 60, lambda: 1 / 0), "ancien")

    def test_failure_pause(self):
        n = []

        def boom():
            n.append(1)
            raise fetch.UpstreamError("down")
        for _ in range(5):
            with self.assertRaises(fetch.UpstreamError):
                self.cache.get("k", 60, boom)
        self.assertEqual(len(n), 1)                   # pas de rafale après une panne

    def test_disk_roundtrip(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            fetch.Cache(d).get("k", 60, lambda: [1, 2])
            self.assertEqual(fetch.Cache(d).get("k", 60, lambda: 1 / 0), [1, 2])

    def test_key_normalisation(self):
        self.assertEqual(fetch.make_key("m", lat=45.7350001, lon=-1.235, model=None),
                         fetch.make_key("m", model="", lon=-1.2350004, lat=45.735))
        self.assertNotEqual(fetch.make_key("m", lat=45.735, model="gwam"),
                            fetch.make_key("m", lat=45.735, model="ewam"))


class GetJsonTests(Base):
    def test_retry_with_backoff(self):
        up = FakeUpstream(fail=2)
        sleeps = []
        with mock.patch.object(fetch, "_urlopen", up), \
                mock.patch.object(fetch, "_sleep", sleeps.append):
            fetch.get_json(sources.MARINE_URL, {"a": 1})
        self.assertEqual(len(up.calls), 3)
        self.assertLess(sleeps[0], sleeps[1])       # délai croissant

    def test_no_retry_on_4xx(self):
        up = FakeUpstream(fail=9, status=400)
        with mock.patch.object(fetch, "_urlopen", up):
            with self.assertRaises(fetch.UpstreamError):
                fetch.get_json(sources.MARINE_URL, {})
        self.assertEqual(len(up.calls), 1)

    def test_daily_budget(self):
        up = FakeUpstream()
        with mock.patch.object(fetch, "_urlopen", up), \
                mock.patch.object(fetch, "BUDGET", fetch.DailyBudget({"open-meteo": 2})):
            fetch.get_json(sources.MARINE_URL, {})
            fetch.get_json(sources.MARINE_URL, {})
            with self.assertRaises(fetch.BudgetExceeded):
                fetch.get_json(sources.MARINE_URL, {})
        self.assertEqual(len(up.calls), 2)

    def test_open_meteo_daily_budget_under_terms(self):
        self.assertLess(fetch.DAILY_BUDGET["open-meteo"], 10000)
        self.assertLessEqual(fetch.DAILY_BUDGET["candhis"], 150)


class HttpConcurrencyTests(Base):
    """De bout en bout : N visiteurs simultanés sur /api/forecast -> 2 appels sortants
    (marine + vent), puis /api/overview et d'autres `past` ne refont aucun appel."""

    def setUp(self):
        super().setUp()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self):
        self.httpd.shutdown()
        super().tearDown()

    def get(self, path):
        c = http.client.HTTPConnection("127.0.0.1", self.httpd.server_address[1], timeout=30)
        c.request("GET", path)
        r = c.getresponse()
        return r, r.read()

    def test_concurrent_requests_one_upstream_call(self):
        spot = next(iter(server.SPOTS))
        up = FakeUpstream(delay=0.3)
        with mock.patch.object(fetch, "_urlopen", up):
            with ThreadPoolExecutor(30) as ex:
                res = list(ex.map(lambda _: self.get(f"/api/forecast?spot={spot}"), range(30)))
            self.assertTrue(all(r.status == 200 for r, _ in res))
            self.assertEqual(len(up.calls), 2, up.calls)          # 1 marine + 1 vent
            r, body = self.get(f"/api/forecast?spot={spot}&past=0")
            self.assertEqual(r.status, 200)
            self.assertEqual(len(up.calls), 2)                    # autre `past` : même entrée
            self.assertIn("max-age", r.getheader("Cache-Control"))
            data = json.loads(body)
            self.assertEqual(data["evals"][0]["time"][:10], dt.date.today().isoformat())
            self.assertNotIn("home", data)

    def test_upstream_down_no_cache_gives_503(self):
        spot = next(iter(server.SPOTS))
        with mock.patch.object(fetch, "_urlopen", FakeUpstream(fail=99)):
            r, _ = self.get(f"/api/forecast?spot={spot}")
        self.assertEqual(r.status, 503)
        self.assertEqual(r.getheader("Cache-Control"), "no-store")

    def test_unknown_model_not_forwarded(self):
        spot = next(iter(server.SPOTS))
        up = FakeUpstream()
        with mock.patch.object(fetch, "_urlopen", up):
            self.get(f"/api/forecast?spot={spot}&model=nimportequoi")
            self.get(f"/api/forecast?spot={spot}&model=autre_chose")
        self.assertEqual(len(up.calls), 2)                        # même clé « auto »
        self.assertFalse(any("nimportequoi" in u for u in up.calls))


if __name__ == "__main__":
    unittest.main()
