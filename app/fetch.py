"""
Appels sortants sobres, partagés par tous les visiteurs.

Tout appel vers une API source (Open-Meteo, CANDHIS) passe par ici :

  Cache.get(key, ttl, fn)  cache mémoire + disque, PARTAGÉ entre visiteurs ;
                           une seule requête en vol par clé (single-flight : 50 visiteurs
                           simultanés -> 1 appel) ; en cas d'échec, renvoi de la dernière
                           donnée connue (périmée) ; après un échec sans donnée connue,
                           pause de FAIL_PAUSE s avant de retenter (pas de rafale).
  get_json(url, params)    timeout, nouvel essai avec délai croissant, débit global
                           borné (seau à jetons) et budget QUOTIDIEN par source
                           (Open-Meteo : < 10 000 appels/jour ; CANDHIS : 150/jour).
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = "surfcast/0.2 (+https://github.com/calaxo/surfcast)"
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")

# Budgets quotidiens (UTC) par source : bien en dessous des conditions des fournisseurs.
DAILY_BUDGET = {"open-meteo": 5000, "candhis": 120}
FAIL_PAUSE = 60            # s : après un échec sans donnée de secours, on ne réessaie pas tout de suite
MAX_STALE = 48 * 3600      # s : au-delà, une donnée périmée n'est plus servie


class UpstreamError(Exception):
    """La source n'a pas répondu (ou budget épuisé) et aucune donnée de secours n'existe."""


class BudgetExceeded(UpstreamError):
    pass


# --------------------------------------------------------------------------- débit

class RateLimiter:
    """Seau à jetons global, thread-safe : `rate` appels/s, rafale de `burst`."""

    def __init__(self, rate: float, burst: int):
        self.rate, self.burst = rate, burst
        self.tokens = float(burst)
        self.stamp = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self.lock:
                now = time.monotonic()
                self.tokens = min(self.burst, self.tokens + (now - self.stamp) * self.rate)
                self.stamp = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                wait = (1 - self.tokens) / self.rate
            time.sleep(wait)


class DailyBudget:
    """Compteur d'appels par source, remis à zéro chaque jour (UTC)."""

    def __init__(self, limits: dict):
        self.limits = dict(limits)
        self.day = None
        self.counts: dict[str, int] = {}
        self.lock = threading.Lock()

    def take(self, source: str) -> None:
        with self.lock:
            today = time.strftime("%Y-%m-%d", time.gmtime())
            if today != self.day:
                self.day, self.counts = today, {}
            n = self.counts.get(source, 0)
            if n >= self.limits.get(source, 1000):
                raise BudgetExceeded(f"budget quotidien {source} épuisé ({n})")
            self.counts[source] = n + 1

    def used(self, source: str) -> int:
        with self.lock:
            return self.counts.get(source, 0)


LIMITER = RateLimiter(rate=5.0, burst=10)    # Open-Meteo tolère 600/min ; on reste très en dessous
BUDGET = DailyBudget(DAILY_BUDGET)


def _urlopen(req, timeout):          # point d'injection pour les tests
    return urllib.request.urlopen(req, timeout=timeout)


def _sleep(seconds):                 # idem (délai de nouvel essai)
    time.sleep(seconds)


def get_json(url: str, params: dict, *, source: str = "open-meteo", headers: dict | None = None,
             timeout: float = 15, retries: int = 2, backoff: float = 1.0) -> dict:
    """GET JSON avec timeout, `retries` nouveaux essais (délai backoff·2^i + aléa) sur erreur
    réseau / 5xx / 429. Une 4xx (hors 429) n'est pas réessayée : la requête est fausse."""
    full = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
    req = urllib.request.Request(full, headers={"User-Agent": USER_AGENT, **(headers or {})})
    last = None
    for attempt in range(retries + 1):
        if attempt:
            _sleep(backoff * (2 ** (attempt - 1)) + random.uniform(0, backoff / 2))
        BUDGET.take(source)
        LIMITER.acquire()
        try:
            with _urlopen(req, timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last = e
            if e.code != 429 and e.code < 500:
                break
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            last = e
    raise UpstreamError(f"{source} : {last}")


# --------------------------------------------------------------------------- cache

def make_key(prefix: str, **parts) -> str:
    """Clé normalisée : flottants arrondis (45.7350001 == 45.735), ordre des champs fixe,
    None == "". Hachée pour donner un nom de fichier sûr."""
    norm = {k: (round(v, 3) if isinstance(v, float) else ("" if v is None else v))
            for k, v in sorted(parts.items())}
    digest = hashlib.sha256(json.dumps(norm, sort_keys=True).encode()).hexdigest()[:20]
    return f"{prefix}_{digest}"


class _Flight:
    __slots__ = ("done", "value", "error")

    def __init__(self):
        self.done = threading.Event()
        self.value = None
        self.error = None


class Cache:
    def __init__(self, directory: str | None = CACHE_DIR):
        self.dir = directory
        self.mem: dict[str, tuple[float, object]] = {}
        self.failed: dict[str, float] = {}
        self.flights: dict[str, _Flight] = {}
        self.lock = threading.Lock()

    # -- disque (survit aux redémarrages ; volume Docker en prod)
    def _path(self, key):
        return os.path.join(self.dir, f"{key}.json") if self.dir else None

    def _load(self, key):
        p = self._path(key)
        if not p or not os.path.isfile(p):
            return None
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
            return float(d["t"]), d["v"]
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def _store(self, key, entry):
        p = self._path(key)
        if not p:
            return
        try:
            os.makedirs(self.dir, exist_ok=True)
            tmp = f"{p}.{threading.get_ident()}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"t": entry[0], "v": entry[1]}, f, ensure_ascii=False)
            os.replace(tmp, p)
        except OSError:
            pass

    def _entry(self, key):
        e = self.mem.get(key)
        if e is None:
            e = self._load(key)
            if e is not None:
                self.mem[key] = e
        return e

    def get(self, key: str, ttl: float, fn, max_stale: float = MAX_STALE):
        now = time.time()
        with self.lock:
            entry = self._entry(key)
            if entry and now - entry[0] < ttl:
                return entry[1]
            stale = entry[1] if entry and now - entry[0] < ttl + max_stale else None
            if stale is None and now - self.failed.get(key, 0) < FAIL_PAUSE:
                raise UpstreamError("source indisponible (nouvel essai sous peu)")
            flight = self.flights.get(key)
            leader = flight is None
            if leader:
                flight = self.flights[key] = _Flight()

        if not leader:                      # quelqu'un est déjà en train de chercher
            flight.done.wait(120)
            if flight.error is None and flight.done.is_set():
                return flight.value
            if stale is not None:
                return stale
            raise UpstreamError(str(flight.error or "délai dépassé"))

        try:
            value = fn()
            entry = (time.time(), value)
            with self.lock:
                self.mem[key] = entry
                self.failed.pop(key, None)
            self._store(key, entry)
            flight.value = value
            return value
        except Exception as e:  # noqa: BLE001 — toute panne de source -> secours
            flight.error = e
            with self.lock:
                self.failed[key] = time.time()
            if stale is not None:
                return stale
            raise e if isinstance(e, UpstreamError) else UpstreamError(str(e)) from e
        finally:
            with self.lock:
                self.flights.pop(key, None)
            flight.done.set()


CACHE = Cache()
