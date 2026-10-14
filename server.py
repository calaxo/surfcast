"""
Serveur web de Surfcast (stdlib uniquement, dockerisable).

Endpoints JSON publics (cache serveur partagé + Cache-Control) :
  /api/spots, /api/config          -> config des spots (rien de personnel)
  /api/forecast?spot=&model=&level=&past=  -> prévision (score + explication)
  /api/overview, /api/ranking, /api/buoy
Endpoints PERSONNELS (cookie propriétaire, jamais mis en cache) :
  /api/me                          -> {owner, home} ; owner=false pour les visiteurs
  /api/sessions?model=             -> journal + boucle de vérification (401 sinon)
  POST /api/login {"key": ...}, POST /api/logout

Sert web/index.html à la racine.

    python server.py            # http://localhost:8080
    python server.py --port 9000
"""
import hashlib
import hmac
import json
import mimetypes
import os
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(__file__))
from app import sources, science, sessions as sess_mod, daylight as dl, buoy  # noqa: E402
from app.fetch import UpstreamError  # noqa: E402

HERE = os.path.dirname(__file__)
# Dossier statique servi : en prod = le front React buildé (frontend/dist), sinon le
# vieux web/ (dev stdlib). Surchargeable par SURFCAST_STATIC (ex: /app/static en Docker).
_DIST = os.path.join(HERE, "frontend", "dist")
STATIC_DIR = os.environ.get("SURFCAST_STATIC") or (_DIST if os.path.isdir(_DIST) else os.path.join(HERE, "web"))
WEB = STATIC_DIR  # rétro-compat
CONFIG = sources.load_config(os.path.join(HERE, "spots.yaml"))
HOME = CONFIG.get("home")
SPOTS = CONFIG.get("spots", {})


def _sessions_path():
    """Journal de sessions : données PERSONNELLES, hors du dépôt git.

    Ordre : $SURFCAST_SESSIONS (ex : fichier monté en volume en prod), puis
    sessions.json local (git-ignoré), puis l'exemple anonymisé sessions.example.json."""
    env = os.environ.get("SURFCAST_SESSIONS")
    if env:
        return env
    local = os.path.join(HERE, "sessions.json")
    return local if os.path.isfile(local) else os.path.join(HERE, "sessions.example.json")


class _SessionStore:
    """Journal relu à chaud si le fichier change (pas besoin de redémarrer)."""

    def __init__(self):
        self.lock = threading.Lock()
        self.stamp = None
        self.data = {"sessions": [], "learned_rules": []}

    def get(self):
        path = _sessions_path()
        try:
            stamp = (path, os.path.getmtime(path))
        except OSError:
            return {"sessions": [], "learned_rules": []}
        with self.lock:
            if stamp != self.stamp:
                try:
                    self.data = sess_mod.load_sessions(path)
                except (OSError, ValueError):
                    self.data = {"sessions": [], "learned_rules": []}
                self.stamp = stamp
            return self.data


SESSIONS = _SessionStore()

# --- Accès propriétaire -------------------------------------------------------------
# Une clé secrète (env SURFCAST_OWNER_KEY, ou fichier SURFCAST_OWNER_KEY_FILE) ; jamais
# dans le dépôt. Sans clé configurée, PERSONNE n'accède aux données perso (fermé par
# défaut). La saisir une fois sur /connexion pose un cookie HttpOnly signé (HMAC).
COOKIE = "surfcast_owner"
COOKIE_MAX_AGE = 180 * 24 * 3600
_LOGIN_LOCK = threading.Lock()
_LOGIN_TRIES: list[float] = []
LOGIN_MAX_PER_MIN = 10


def _owner_key():
    k = os.environ.get("SURFCAST_OWNER_KEY", "").strip()
    f = os.environ.get("SURFCAST_OWNER_KEY_FILE")
    if not k and f:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                k = fh.read().strip()
        except OSError:
            k = ""
    return k if len(k) >= 16 else None     # clé trop courte = refusée (fermé)


def _owner_token(key):
    return hmac.new(key.encode(), b"surfcast-owner-v1", hashlib.sha256).hexdigest()


def _login_allowed():
    now = time.monotonic()
    with _LOGIN_LOCK:
        _LOGIN_TRIES[:] = [t for t in _LOGIN_TRIES if now - t < 60]
        if len(_LOGIN_TRIES) >= LOGIN_MAX_PER_MIN:
            return False
        _LOGIN_TRIES.append(now)
        return True


# Validation des paramètres de requête : listes fermées / bornes, rien d'arbitraire
# (chaque valeur distincte = une clé de cache = potentiellement un appel sortant).
MODELS = {"meteofrance_wave", "gwam", "ewam"}
_LEVELS = set(getattr(science, "LEVELS", {}) or ("debutant",))
MAX_PAST_DAYS = sources.FETCH_PAST_DAYS
MAX_URL = 2048

# Cache-Control des réponses JSON publiques (la donnée change au plus toutes les heures).
CC_FORECAST = "public, max-age=600, stale-while-revalidate=1800"
CC_BUOY = "public, max-age=300"
CC_STATIC_JSON = "public, max-age=3600"
CC_PRIVATE = "private, no-store"


def _clean_model(v):
    return v if v in MODELS else None


def _clean_level(v):
    return v if v in _LEVELS else "debutant"


def _clean_past(v):
    try:
        return max(0, min(int(v), MAX_PAST_DAYS))
    except (TypeError, ValueError):
        return 4


def build_evals(spot, days=3, model=None, level="debutant", past_days=0):
    hours = sources.merged_hours(spot["latitude"], spot["longitude"], spot["timezone"],
                                 days=days, model=model, past_days=past_days)
    conds = []
    for h in hours:
        # TAILLE + période = mer TOTALE (ce que voient les surfeurs / sites de report).
        sh = h["wave_height"] if h["wave_height"] is not None else h["swell_wave_height"]
        sp = h["wave_period"] if h["wave_period"] is not None else h["swell_wave_peak_period"]
        # ORIENTATION = direction de la HOULE (groundswell), pas de la mer totale : cette
        # dernière est biaisée par la mer du vent (vent de terre) et pointe à contresens.
        sd = h["swell_wave_direction"] if h["swell_wave_direction"] is not None else h["wave_direction"]
        if sh is None or sp is None:
            continue
        conds.append(science.Conditions(
            time=h["time"], swell_h=sh, swell_period=sp, swell_dir=sd,
            wind_wave_h=h["wind_wave_height"], wind_speed=h["wind_speed_10m"],
            wind_dir=h["wind_direction_10m"], tide_m=h.get("sea_level_height_msl"),
            # trains de houle séparés : primaire = swell_wave_*, secondaire = secondary_swell_wave_*
            sw1_h=h.get("swell_wave_height"), sw1_t=h.get("swell_wave_peak_period"),
            sw1_dir=h.get("swell_wave_direction"),
            sw2_h=h.get("secondary_swell_wave_height"), sw2_t=h.get("secondary_swell_wave_period"),
            sw2_dir=h.get("secondary_swell_wave_direction"),
            # thermique (conseil de combinaison uniquement, pas de score)
            water_temp=h.get("sea_surface_temperature"),
            air_temp=h.get("temperature_2m"),
            feels_like=h.get("apparent_temperature")))
    # Marée annotée PAR JOUR (normalisation basse/pleine + marnage corrects par jour,
    # sinon un lot de 6 jours mélange vive-eau et morte-eau).
    by_day = {}
    for c in conds:
        by_day.setdefault(c.time[:10], []).append(c)
    for group in by_day.values():
        science.annotate_tide(group)
    return [science.evaluate(c, spot, level=level) for c in conds]


def evals_to_dicts(evals):
    return [{"time": e.time, "score": e.score, "label": e.label, "power": e.power_kw_m,
             "wave_h": e.wave_h, "headline": e.headline,
             "drivers": e.drivers, "explanation": e.explanation} for e in evals]


def tide_events(evals):
    """Pleines et basses mers par jour, à partir du niveau de mer HORAIRE des evals.

    Un extremum tombe rarement pile sur une heure ronde : on ajuste le sommet par une
    parabole passant par les 3 points horaires qui l'encadrent (précision ~±10 min, ce
    qui suffit pour "PM vers 18h05"). Les hauteurs sont relatives au niveau moyen
    (Open-Meteo `sea_level_height_msl`), pas au zéro hydrographique du SHOM : on les
    affiche donc comme des écarts (+2,1 m / −2,0 m), et surtout le MARNAGE.
    La détection se fait sur la série continue (pas jour par jour) pour ne pas rater
    un extremum à 23 h ou 0 h."""
    pts = []
    for i, e in enumerate(evals):
        lvl = (e.drivers.get("maree") or {}).get("level")
        if lvl is not None:
            pts.append((i, e.time, lvl))
    out = {}
    for k in range(1, len(pts) - 1):
        (_, _t0, v0), (_, t1, v1), (_, _t2, v2) = pts[k - 1], pts[k], pts[k + 1]
        if v1 >= v0 and v1 > v2 or v1 > v0 and v1 >= v2:
            typ = "PM"
        elif v1 <= v0 and v1 < v2 or v1 < v0 and v1 <= v2:
            typ = "BM"
        else:
            continue
        denom = v0 - 2 * v1 + v2
        dt = (0.5 * (v0 - v2) / denom) if denom else 0.0      # décalage en heures, |dt| ≤ 0.5
        peak = v1 - 0.25 * (v0 - v2) * dt if denom else v1
        hour = int(t1[11:13]) + dt
        day = t1[:10]
        if hour >= 24:            # l'ajustement a poussé l'extremum sur le jour suivant
            hour -= 24
            day = _next_day(day)
        elif hour < 0:
            hour += 24
            day = _prev_day(day)
        hh, mm = int(hour), int(round((hour % 1) * 60))
        if mm == 60:
            hh, mm = hh + 1, 0
        out.setdefault(day, []).append({"type": typ, "time": f"{hh:02d}:{mm:02d}",
                                        "height": round(peak, 2)})
    res = {}
    by_day = {}
    for e in evals:
        by_day.setdefault(e.time[:10], e)
    for day, first in by_day.items():
        m = first.drivers.get("maree") or {}
        res[day] = {"events": sorted(out.get(day, []), key=lambda x: x["time"]),
                    "range": m.get("range"), "amplitude": m.get("amplitude")}
    return res


def _next_day(iso):
    import datetime as _dt
    return (_dt.date.fromisoformat(iso) + _dt.timedelta(days=1)).isoformat()


def _prev_day(iso):
    import datetime as _dt
    return (_dt.date.fromisoformat(iso) - _dt.timedelta(days=1)).isoformat()


def daylight_for_days(spot, dates):
    """Fenêtre de lumière (lever/coucher/crépuscule) pour chaque date d'un lot d'evals."""
    return {d: dl.sun_events(spot["latitude"], spot["longitude"], d) for d in dates}


def best_in_light(day_evals, spot):
    """Meilleur créneau du jour LIMITÉ à la lumière (on ne recommande jamais dans le noir)."""
    if not day_evals:
        return None
    date = day_evals[0].time[:10]
    ev = dl.sun_events(spot["latitude"], spot["longitude"], date)
    lit = [e for e in day_evals if dl.in_light(e.time[11:16], ev)]
    return max(lit or day_evals, key=lambda e: e.score)


def overview(model=None, level="debutant"):
    """Score du jour (meilleur créneau de jour) pour chaque spot — pour la carte."""
    out = []
    for key, spot in SPOTS.items():
        try:
            evals = build_evals(spot, days=3, model=model, level=level)  # days=3 = même cache que /api/forecast
            today = [e for e in evals if e.time[:10] == evals[0].time[:10]] if evals else []
            best = best_in_light(today, spot) if today else None
        except Exception:
            best = None
        out.append({
            "key": key, "name": spot["name"], "region": spot.get("region"),
            "lat": spot["latitude"], "lon": spot["longitude"],
            "drive_min": spot.get("drive_min"), "level": spot.get("level"),
            "today_score": best.score if best else None,
            "today_label": best.label if best else None,
            "best_time": best.time[11:16] if best else None,
        })
    return out


def ranking(model=None, level="debutant"):
    """Pour chaque spot : le meilleur créneau de CHAQUE jour → tableau 'où surfer'."""
    out = []
    for key, spot in SPOTS.items():
        try:
            evals = build_evals(spot, days=3, model=model, level=level)
        except Exception:
            evals = []
        by_day = {}
        for e in evals:
            by_day.setdefault(e.time[:10], []).append(e)
        days = []
        for day in sorted(by_day):
            b = best_in_light(by_day[day], spot)
            if b:
                ev = dl.sun_events(spot["latitude"], spot["longitude"], day)
                days.append({"date": day, "score": b.score, "label": b.label,
                             "best_time": b.time[11:16], "wave_h": b.wave_h,
                             "headline": b.headline, "surf_light": ev["surf_light"]})
        out.append({"key": key, "name": spot["name"], "region": spot.get("region"),
                    "drive_min": spot.get("drive_min"), "level": spot.get("level"),
                    "days": days})
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = "surfcast"
    sys_version = ""

    def log_message(self, *a):
        pass                      # pas de journal d'accès (rien de perso dans les logs)

    # -- propriétaire
    def _cookie(self, name):
        for part in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == name:
                return v
        return None

    def is_owner(self):
        key = _owner_key()
        tok = self._cookie(COOKIE)
        return bool(key and tok and hmac.compare_digest(tok, _owner_token(key)))

    def _spot(self, qs):
        return SPOTS.get(qs.get("spot", [next(iter(SPOTS))])[0])

    def do_GET(self):
        if len(self.path) > MAX_URL:
            return self._json({"error": "requête trop longue"}, 414)
        u = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(u.query)
        model = _clean_model(qs.get("model", [None])[0])
        level = _clean_level(qs.get("level", ["debutant"])[0])

        if u.path in ("/api/spots", "/api/config"):
            # /api/config : public uniquement. Le point de départ (domicile) est perso -> /api/me
            body = SPOTS if u.path == "/api/spots" else {"spots": SPOTS}
            return self._json(body, cache=CC_STATIC_JSON)

        if u.path == "/api/me":
            owner = self.is_owner()
            return self._json({"owner": owner, "home": HOME if owner else None}, cache=CC_PRIVATE)

        if u.path == "/api/sessions":
            if not self.is_owner():
                # 401 SANS WWW-Authenticate : pas de fenêtre de connexion du navigateur
                return self._json({"error": "connexion requise"}, 401, cache=CC_PRIVATE)
            return self._json(sess_mod.learned_insights(SESSIONS.get(), SPOTS, model=model),
                              cache=CC_PRIVATE)

        if u.path == "/api/overview":
            return self._json(overview(model, level), cache=CC_FORECAST)

        if u.path == "/api/ranking":
            return self._json(ranking(model, level), cache=CC_FORECAST)

        if u.path == "/api/forecast":
            spot = self._spot(qs)
            if not spot:
                return self._json({"error": "spot inconnu"}, 404)
            past = _clean_past(qs.get("past", ["4"])[0])
            try:
                evals = build_evals(spot, 3, model, level, past_days=past)
            except UpstreamError:
                return self._json({"error": "source météo indisponible, réessayer plus tard"}, 503,
                                  extra={"Retry-After": "60"})
            dates = sorted({e.time[:10] for e in evals})
            return self._json({"spot": spot, "model": model or "auto",
                               "evals": evals_to_dicts(evals),
                               "daylight": daylight_for_days(spot, dates),
                               "tides": tide_events(evals)}, cache=CC_FORECAST)

        if u.path == "/api/buoy":
            # nowcast bouée CANDHIS la plus proche du spot (None si pas de token)
            spot = self._spot(qs)
            if not spot:
                return self._json({"available": False}, 404)
            data = buoy.latest(spot["latitude"], spot["longitude"]) if buoy.available() else None
            return self._json({"available": buoy.available(), "buoy": data}, cache=CC_BUOY)

        if u.path.startswith("/api/"):
            return self._json({"error": "inconnu"}, 404)
        # --- statique : sert le SPA buildé (dist) avec fallback SPA sur index.html ---
        return self._serve_static(u.path)

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        if u.path not in ("/api/login", "/api/logout"):
            return self._json({"error": "inconnu"}, 404)
        # anti-CSRF : la requête doit venir de la même origine que le site
        origin = self.headers.get("Origin")
        if origin and urllib.parse.urlparse(origin).netloc != self.headers.get("Host"):
            return self._json({"error": "origine refusée"}, 403)
        if u.path == "/api/logout":
            return self._json({"owner": False}, cache=CC_PRIVATE,
                              extra={"Set-Cookie": self._set_cookie("", 0)})
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if not 0 < n <= 4096:
            return self._json({"error": "requête invalide"}, 400)
        try:
            given = str(json.loads(self.rfile.read(n).decode("utf-8")).get("key", ""))
        except (ValueError, AttributeError, UnicodeDecodeError):
            return self._json({"error": "requête invalide"}, 400)
        if not _login_allowed():
            return self._json({"error": "trop d'essais, patienter une minute"}, 429,
                              extra={"Retry-After": "60"})
        key = _owner_key()
        ok = bool(key) and hmac.compare_digest(hashlib.sha256(given.encode()).digest(),
                                               hashlib.sha256(key.encode()).digest())
        if not ok:
            return self._json({"error": "clé incorrecte"}, 403, cache=CC_PRIVATE)
        return self._json({"owner": True}, cache=CC_PRIVATE,
                          extra={"Set-Cookie": self._set_cookie(_owner_token(key), COOKIE_MAX_AGE)})

    @staticmethod
    def _set_cookie(value, max_age):
        return (f"{COOKIE}={value}; Max-Age={max_age}; Path=/; HttpOnly; Secure; "
                f"SameSite=Strict")

    def _serve_static(self, path):
        rel = path.lstrip("/") or "index.html"
        root = os.path.realpath(STATIC_DIR)
        full = os.path.realpath(os.path.join(root, rel))
        # anti path-traversal : rester DANS STATIC_DIR (commonpath, pas un simple préfixe
        # de chaîne qui laisserait passer un dossier voisin « static2/ »)
        if os.path.commonpath([root, full]) != root:
            return self._send(403, "text/plain", b"forbidden")
        if os.path.isfile(full):
            return self._file(full)
        # routes client (vite-plugin-pages : /carte, /sessions, ...) → index.html
        if "." not in os.path.basename(rel):
            idx = os.path.join(STATIC_DIR, "index.html")
            if os.path.isfile(idx):
                return self._file(idx)
        return self._send(404, "text/plain", b"not found")

    def _json(self, obj, code=200, cache=None, extra=None):
        headers = {"Cache-Control": cache if code == 200 and cache else "no-store"}
        if cache == CC_PRIVATE:
            headers["Vary"] = "Cookie"
        headers.update(extra or {})
        self._send(code, "application/json; charset=utf-8",
                   json.dumps(obj, ensure_ascii=False).encode("utf-8"), extra=headers)

    def _file(self, full_path):
        ctype = mimetypes.guess_type(full_path)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        with open(full_path, "rb") as f:
            body = f.read()
        base = os.path.basename(full_path)
        # PWA : index.html + service worker jamais mis en cache HTTP (maj immédiate) ;
        # les assets hashés (Vite) peuvent être cachés longtemps.
        if base in ("index.html", "sw.js", "registerSW.js", "manifest.webmanifest"):
            cache = "no-cache"
        elif "/assets/" in full_path.replace("\\", "/"):
            cache = "public, max-age=31536000, immutable"
        else:
            cache = "public, max-age=3600"
        self._send(200, ctype, body, extra={"Cache-Control": cache})

    def _send(self, code, ctype, body, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        # Pas de CORS « * » : le front est servi par ce même serveur (même origine) et
        # Vite proxifie /api en dev. Évite que des sites tiers utilisent l'API comme relais.
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)


def main():
    port = 8080
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])
    print(f"Surfcast sur http://localhost:{port}")
    if not _owner_key():
        print("SURFCAST_OWNER_KEY absent : données personnelles inaccessibles (mode public seul)")
    httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    httpd.daemon_threads = True
    httpd.serve_forever()


if __name__ == "__main__":
    main()
