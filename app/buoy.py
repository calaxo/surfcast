"""
Bouées CANDHIS (Cerema) — nowcast : état de mer MESURÉ au large, en ce moment.

Vérité terrain temps réel à comparer au modèle. La bouée est au large → c'est l'état de
mer d'entrée (pas les vagues au bord). On prend la bouée ACTIVE la plus proche du spot
dans le Golfe de Gascogne (zone Z07) — l'idéale (Oléron Large 01704) est parfois HS, on
bascule alors sur la suivante (ex : Noirmoutier), en affichant la distance pour juger.

⚠️ Quota API = 150 requêtes/jour. Design économe (cache partagé de app/fetch.py, budget
quotidien plafonné à 120, une seule requête en vol, dernière mesure servie si panne) :
  - 1 appel getCampListeTR (toutes les bouées d'un coup) mis en cache 30 min → ≤ 48 req/jour.
  - coords des bouées de la zone en cache 30 j (bougent jamais).
Activation : variable d'env CANDHIS_TOKEN. Sans token → None partout (feature absente).
Token : demande à candhis@cerema.fr. Doc : https://candhis.cerema.fr/API/v1/
"""
from __future__ import annotations
import math
import os

from .fetch import CACHE, UpstreamError, get_json, make_key

BASE = "https://candhis.cerema.fr/API/v1"
TOKEN = os.environ.get("CANDHIS_TOKEN")
ZONE = "Z07"              # Golfe de Gascogne
MAX_DIST_KM = 200         # au-delà, la bouée n'est plus représentative → on n'affiche pas
MISSING = 900.0           # 999.9999 = valeur manquante

STATIONS_TTL = 30 * 24 * 3600
LIVE_TTL = 30 * 60         # nowcast : 30 min (≤ 48 appels/jour sur un quota de 150)


def available() -> bool:
    return bool(TOKEN)


def _get(func: str, params: dict) -> dict:
    d = get_json(f"{BASE}/{func}", params, source="candhis", timeout=15, retries=1,
                 headers={"Authorization": TOKEN, "content-type": "application/json"})
    if str(d.get("success")).lower() != "true":
        raise UpstreamError(f"CANDHIS {func} : réponse en échec")
    return d


def _haversine(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _stations() -> list[dict]:
    """Bouées de la zone Golfe de Gascogne avec coords. Cache 30 j (rarement changées)."""
    try:
        return CACHE.get(make_key("candhis_stations", zone=ZONE), STATIONS_TTL, _fetch_stations)
    except UpstreamError:
        return []


def _fetch_stations() -> list[dict]:
    zone = _get("getCampZone.php", {"zone": ZONE})
    out = []
    for code in zone.get("results", []):
        code = code[0] if isinstance(code, list) else code
        try:
            info = _get("getCampInfos.php", {"camp": code})
        except UpstreamError:
            continue
        if not info.get("results"):
            continue
        row = info["results"][0]      # [Nom, Latitude, Longitude, Profondeur, Directionnel, Capteur]
        try:
            out.append({"code": code, "name": row[0], "lat": float(row[1]), "lon": float(row[2])})
        except (ValueError, IndexError):
            continue
    if not out:
        raise UpstreamError("CANDHIS : aucune bouée")   # ne pas graver un vide en cache
    return out


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f >= MISSING else round(f, 2)


def _live() -> dict:
    """Dernière mesure de TOUTES les bouées directionnelles, en 1 appel. Cache 30 min.
    Retourne {code: {time, hs, period, dir, temp}} (bouées sans donnée exclues)."""
    try:
        return CACHE.get(make_key("candhis_live", type=2), LIVE_TTL, _fetch_live)
    except UpstreamError:
        return {}


def _fetch_live() -> dict:
    d = _get("getCampListeTR.php", {"type": "2"})   # type 2 = directionnel H13
    out = {}
    if d and d.get("results"):
        ent = [h.lower() for h in d["entete"]]

        def col(row, *keys):
            for i, h in enumerate(ent):
                if any(k in h for k in keys):
                    return row[i]
            return None
        for row in d["results"]:
            code = col(row, "campagne")
            hs = _num(col(row, "h1/3", "hm0"))
            if not code or hs is None:
                continue
            out[code] = {"time": col(row, "date"), "hs": hs,
                         "period": _num(col(row, "th1/3", "t. au pic", "t02")),
                         "dir": _num(col(row, "dir")), "temp": _num(col(row, "temp"))}
    if not out:
        raise UpstreamError("CANDHIS : aucune mesure")
    return out


def latest(lat: float, lon: float) -> dict | None:
    """Bouée ACTIVE la plus proche du spot (< MAX_DIST_KM) + sa dernière mesure. None sinon."""
    if not TOKEN:
        return None
    live = _live()
    if not live:
        return None
    cands = [(s, _haversine(lat, lon, s["lat"], s["lon"])) for s in _stations() if s["code"] in live]
    if not cands:
        return None
    s, dist = min(cands, key=lambda x: x[1])
    if dist > MAX_DIST_KM:
        return None
    m = live[s["code"]]
    return {"name": s["name"], "code": s["code"], "dist_km": round(dist),
            "time": m["time"], "hs": m["hs"], "period": m["period"],
            "dir": m["dir"], "temp": m["temp"]}
