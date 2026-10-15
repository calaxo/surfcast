"""Tests hors-ligne (stdlib) : validation des paramètres, anti path-traversal, CORS,
chargement du journal de sessions, accès propriétaire. Lancer : python -m pytest"""
import http.client
import json
import os
import sys
import tempfile
import threading
import unittest
from unittest import mock
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import server  # noqa: E402


class ParamTests(unittest.TestCase):
    def test_model(self):
        self.assertEqual(server._clean_model("meteofrance_wave"), "meteofrance_wave")
        self.assertIsNone(server._clean_model(""))
        self.assertIsNone(server._clean_model(None))
        self.assertIsNone(server._clean_model("../../etc/passwd"))
        self.assertIsNone(server._clean_model("x&past_days=9999"))
        self.assertIsNone(server._clean_model("ecmwf_inconnu"))     # liste fermée

    def test_past(self):
        self.assertEqual(server._clean_past("999"), server.MAX_PAST_DAYS)
        self.assertEqual(server._clean_past("-3"), 0)
        self.assertEqual(server._clean_past("abc"), 4)

    def test_level(self):
        self.assertEqual(server._clean_level("confirme"), "confirme")
        self.assertEqual(server._clean_level("<script>"), "debutant")

    def test_sessions_path(self):
        old = os.environ.get("SURFCAST_SESSIONS")
        try:
            os.environ["SURFCAST_SESSIONS"] = "/data/sessions.json"
            self.assertEqual(server._sessions_path(), "/data/sessions.json")
            del os.environ["SURFCAST_SESSIONS"]
            self.assertTrue(server._sessions_path().endswith(("sessions.json", "sessions.example.json")))
        finally:
            if old is not None:
                os.environ["SURFCAST_SESSIONS"] = old

    def test_home_path_and_example(self):
        with mock.patch.dict(os.environ, {"SURFCAST_HOME": "/data/home.json"}):
            self.assertEqual(server._home_path(), "/data/home.json")
        home = server._load_home(os.path.join(ROOT, "home.example.json"))
        self.assertIn("drive_min", home)
        self.assertTrue(set(home["drive_min"]) <= set(server.SPOTS))
        self.assertIsNone(server._load_home(os.path.join(ROOT, "absent.json")))

    def test_example_is_valid(self):
        data = server.sess_mod.load_sessions(os.path.join(ROOT, "sessions.example.json"))
        for s in data["sessions"]:
            self.assertIn(s["spot"], server.SPOTS)


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        static = os.path.join(cls.tmp.name, "static")
        os.makedirs(static)
        with open(os.path.join(static, "index.html"), "w") as f:
            f.write("<html>ok</html>")
        os.makedirs(os.path.join(cls.tmp.name, "static2"))
        with open(os.path.join(cls.tmp.name, "static2", "secret.txt"), "w") as f:
            f.write("secret")
        cls._old_static = server.STATIC_DIR
        server.STATIC_DIR = static
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        server.STATIC_DIR = cls._old_static
        cls.tmp.cleanup()

    def get(self, path, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.httpd.server_address[1], timeout=10)
        c.request("GET", path, headers=headers or {})
        r = c.getresponse()
        return r, r.read()

    def post(self, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.httpd.server_address[1], timeout=10)
        data = json.dumps(body).encode() if body is not None else b""
        c.request("POST", path, body=data, headers={"Content-Type": "application/json", **(headers or {})})
        r = c.getresponse()
        return r, r.read()

    def test_spots_no_wildcard_cors(self):
        r, body = self.get("/api/spots")
        self.assertEqual(r.status, 200)
        self.assertIsNone(r.getheader("Access-Control-Allow-Origin"))
        self.assertEqual(r.getheader("X-Content-Type-Options"), "nosniff")

    def test_static_index(self):
        r, body = self.get("/")
        self.assertEqual(r.status, 200)
        self.assertIn(b"ok", body)

    def test_traversal_blocked(self):
        for p in ("/../static2/secret.txt", "/..%2fstatic2/secret.txt", "/../../server.py"):
            r, body = self.get(p)
            self.assertNotIn(b"secret", body, p)
            self.assertNotIn(b"ThreadingHTTPServer", body, p)


KEY = "cle-de-test-suffisamment-longue"


class OwnerTests(HttpTests):
    """Les visiteurs n'ont ni sessions ni domicile ; le propriétaire les a après connexion."""

    def setUp(self):
        self.env = mock.patch.dict(os.environ, {
            "SURFCAST_OWNER_KEY": KEY,
            "SURFCAST_SESSIONS": os.path.join(ROOT, "sessions.example.json")})
        self.env.start()
        server._LOGIN_TRIES.clear()
        self.verify = mock.patch.object(server.sess_mod, "verify_session",
                                        lambda s, spot, model=None: {"spot": s["spot"], "date": s["date"],
                                                                     "rating_obs": s["rating"]})
        self.verify.start()

    def tearDown(self):
        self.verify.stop()
        self.env.stop()

    def login(self, key=KEY):
        return self.post("/api/login", {"key": key})

    def test_anonymous_has_no_sessions(self):
        r, body = self.get("/api/sessions")
        self.assertEqual(r.status, 401)
        self.assertIsNone(r.getheader("WWW-Authenticate"))     # pas de popup navigateur
        self.assertEqual(r.getheader("Cache-Control"), "no-store")
        self.assertNotIn(b"exemple-offshore", body)

    def test_config_is_public_only(self):
        r, body = self.get("/api/config")
        self.assertNotIn("home", json.loads(body))
        self.assertNotIn(b"drive_min", body)       # temps de route = point de départ deviné
        r, body = self.get("/api/me")
        self.assertEqual(json.loads(body), {"owner": False, "home": None})
        self.assertIn("no-store", r.getheader("Cache-Control"))

    def test_wrong_key(self):
        r, _ = self.login("mauvaise")
        self.assertEqual(r.status, 403)
        self.assertIsNone(r.getheader("Set-Cookie"))

    def test_forged_cookie(self):
        r, _ = self.get("/api/sessions", {"Cookie": "surfcast_owner=" + "0" * 64})
        self.assertEqual(r.status, 401)

    def test_owner_flow(self):
        r, _ = self.login()
        self.assertEqual(r.status, 200)
        cookie = r.getheader("Set-Cookie")
        for flag in ("HttpOnly", "Secure", "SameSite=Strict"):
            self.assertIn(flag, cookie)
        h = {"Cookie": cookie.split(";")[0]}
        r, body = self.get("/api/sessions", h)
        self.assertEqual(r.status, 200)
        self.assertEqual(r.getheader("Cache-Control"), "private, no-store")
        self.assertIn(b"2025-06-14", body)
        r, body = self.get("/api/me", h)
        self.assertTrue(json.loads(body)["owner"])
        home = json.loads(body)["home"]
        self.assertIsNotNone(home)
        self.assertTrue(set(home["drive_min"]) <= set(server.SPOTS))
        r, _ = self.post("/api/logout")
        self.assertIn("Max-Age=0", r.getheader("Set-Cookie"))

    def test_no_key_configured_is_closed(self):
        with mock.patch.dict(os.environ, {"SURFCAST_OWNER_KEY": ""}):
            r, _ = self.login("")
            self.assertEqual(r.status, 403)
            r, _ = self.get("/api/sessions", {"Cookie": "surfcast_owner=" + server._owner_token("")})
            self.assertEqual(r.status, 401)

    def test_cross_origin_login_refused(self):
        r, _ = self.post("/api/login", {"key": KEY}, {"Origin": "https://evil.example"})
        self.assertEqual(r.status, 403)

    def test_login_rate_limited(self):
        for _ in range(server.LOGIN_MAX_PER_MIN):
            self.login("x")
        r, _ = self.login()
        self.assertEqual(r.status, 429)


if __name__ == "__main__":
    unittest.main()
