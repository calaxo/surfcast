"""
Serveur web de Surfcast (stdlib uniquement, dockerisable).

Endpoints JSON :
  /api/spots                       -> config des spots
  /api/forecast?spot=&model=       -> prévision 3 j (score + explication)
  /api/sessions?model=             -> journal + boucle de vérification

Sert web/index.html à la racine.

    python server.py            # http://localhost:8080
    python server.py --port 9000
"""
import json
import mimetypes
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(__file__))
from app import sources, science, sessions as sess_mod, daylight as dl  # noqa: E402

HERE = os.path.dirname(__file__)
# Dossier statique servi : en prod = le front React buildé (frontend/dist), sinon le
# vieux web/ (dev stdlib). Surchargeable par SURFCAST_STATIC (ex: /app/static en Docker).
_DIST = os.path.join(HERE, "frontend", "dist")
STATIC_DIR = os.environ.get("SURFCAST_STATIC") or (_DIST if os.path.isdir(_DIST) else os.path.join(HERE, "web"))
WEB = STATIC_DIR  # rétro-compat
CONFIG = sources.load_config(os.path.join(HERE, "spots.yaml"))
HOME = CONFIG.get("home")
SPOTS = CONFIG.get("spots", {})
SESSIONS = sess_mod.load_sessions(os.path.join(HERE, "sessions.json"))


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
            wind_dir=h["wind_direction_10m"], tide_m=h.get("sea_level_height_msl")))
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
    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(u.query)
        model = qs.get("model", [None])[0]
        level = qs.get("level", ["debutant"])[0]

        if u.path == "/api/spots":
            return self._json(SPOTS)

        if u.path == "/api/config":
            return self._json({"home": HOME, "spots": SPOTS})

        if u.path == "/api/overview":
            return self._json(overview(model, level))

        if u.path == "/api/ranking":
            return self._json(ranking(model, level))

        if u.path == "/api/forecast":
            spot = SPOTS.get(qs.get("spot", [next(iter(SPOTS))])[0])
            if not spot:
                return self._json({"error": "spot inconnu"}, 404)
            try:
                past = int(qs.get("past", ["4"])[0])
            except ValueError:
                past = 4
            evals = build_evals(spot, 3, model, level, past_days=past)
            dates = sorted({e.time[:10] for e in evals})
            return self._json({"spot": spot, "model": model or "auto",
                               "evals": evals_to_dicts(evals),
                               "daylight": daylight_for_days(spot, dates),
                               "home": HOME})

        if u.path == "/api/sessions":
            return self._json(sess_mod.learned_insights(SESSIONS, SPOTS, model=model))

        # --- statique : sert le SPA buildé (dist) avec fallback SPA sur index.html ---
        return self._serve_static(u.path)

    def _serve_static(self, path):
        rel = path.lstrip("/") or "index.html"
        full = os.path.normpath(os.path.join(STATIC_DIR, rel))
        # anti path-traversal : rester dans STATIC_DIR
        if not full.startswith(os.path.normpath(STATIC_DIR)):
            return self._send(403, "text/plain", b"forbidden")
        if os.path.isfile(full):
            return self._file(full)
        # routes client (vite-plugin-pages : /carte, /sessions, ...) → index.html
        if "." not in os.path.basename(rel):
            idx = os.path.join(STATIC_DIR, "index.html")
            if os.path.isfile(idx):
                return self._file(idx)
        return self._send(404, "text/plain", b"not found")

    def _json(self, obj, code=200):
        self._send(code, "application/json; charset=utf-8",
                   json.dumps(obj, ensure_ascii=False).encode("utf-8"))

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
        self.send_header("Access-Control-Allow-Origin", "*")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)


def main():
    port = 8080
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])
    print(f"Surfcast sur http://localhost:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
