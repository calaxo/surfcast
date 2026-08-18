"""
Bouées CANDHIS (Cerema) — nowcast (état de mer mesuré EN CE MOMENT) au large des spots.

Vérité terrain temps réel : la bouée la plus proche donne Hs / période / direction mesurés,
à comparer au modèle (Open-Meteo) et à tes sessions. La bouée est AU LARGE → c'est l'état
de mer d'entrée (pas les vagues au bord), donc ça valide l'input du modèle.

Activation : variable d'environnement CANDHIS_TOKEN (jeton API, forme xxxxxxxx-xxxx-...).
Sans token → toutes les fonctions renvoient None proprement (feature simplement absente).
Demande du token : email à candhis@cerema.fr (nom + domaine d'activité + type de structure).
Doc API : https://candhis.cerema.fr/API/v1/  (getCampZone / getCampInfos / getCampTR).
"""
from __future__ import annotations
import json
import math
import os
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta

BASE = "https://candhis.cerema.fr/API/v1/"
TOKEN = os.environ.get("CANDHIS_TOKEN")
ZONE = "Z07"   # Golfe de Gascogne (côte Atlantique SO)

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
STATIONS_CACHE = os.path.join(CACHE_DIR, "candhis_stations.json")
LATEST_TTL = 30 * 60          # nowcast : la bouée mesure ~toutes les 30 min
STATIONS_TTL = 30 * 24 * 3600  # la liste des bouées bouge rarement


def available() -> bool:
    return bool(TOKEN)


def _get(func: str, params: dict) -> dict | None:
    """Appel GET authentifié à l'API CANDHIS. None si pas de token / erreur / success=False."""
    if not TOKEN:
        return None
    url = BASE + func + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": TOKEN, "content-type": "application/json",
        "User-Agent": "surfcast/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read().decode("utf-8"))
    except Exception:
        return None
    return d if str(d.get("success")).lower() == "true" else None


def _haversine(lat1, lon1, lat2, lon2) -> float:
    """Distance km entre deux points."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def stations() -> list[dict]:
    """Bouées de la zone Golfe de Gascogne avec leurs coordonnées. Cache disque (30 j)."""
    if os.path.isfile(STATIONS_CACHE) and (time.time() - os.path.getmtime(STATIONS_CACHE)) < STATIONS_TTL:
        try:
            with open(STATIONS_CACHE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    zone = _get("getCampZone.php", {"zone": ZONE})
    if not zone:
        return []
    out = []
    for code in zone.get("results", []):
        code = code[0] if isinstance(code, list) else code   # results = liste de codes
        info = _get("getCampInfos.php", {"camp": code})
        if not info or not info.get("results"):
            continue
        row = info["results"][0]        # [Nom, Latitude, Longitude, Profondeur, Directionnel, Capteur]
        try:
            out.append({"code": code, "name": row[0],
                        "lat": float(row[1]), "lon": float(row[2]),
                        "directional": row[4] == "1"})
        except (ValueError, IndexError):
            continue
    if out:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(STATIONS_CACHE, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False)
    return out


def nearest_station(lat: float, lon: float) -> dict | None:
    st = stations()
    if not st:
        return None
    best = min(st, key=lambda s: _haversine(lat, lon, s["lat"], s["lon"]))
    best = {**best, "dist_km": round(_haversine(lat, lon, best["lat"], best["lon"]), 1)}
    return best


def _num(v):
    """Convertit une valeur CANDHIS ; 999.9999 (ou vide) = manquant → None."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f > 900 else round(f, 2)


def _pick(entete, row, *names):
    """Récupère la 1re colonne dont l'entête contient un des mots-clés (insensible)."""
    for i, h in enumerate(entete):
        hl = h.lower()
        if any(n in hl for n in names):
            return row[i]
    return None


def latest(spot_lat: float, spot_lon: float) -> dict | None:
    """Dernière mesure temps réel de la bouée la plus proche du spot. Cache 30 min.
    Retourne {name, code, dist_km, time, hs, period, dir, temp} ou None."""
    st = nearest_station(spot_lat, spot_lon)
    if not st:
        return None
    os.makedirs(CACHE_DIR, exist_ok=True)
    cpath = os.path.join(CACHE_DIR, f"buoy_{st['code']}.json")
    if os.path.isfile(cpath) and (time.time() - os.path.getmtime(cpath)) < LATEST_TTL:
        try:
            with open(cpath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # getCampTR renvoie les mesures depuis dateDeb → on prend la DERNIÈRE ligne non vide.
    deb = (date.today() - timedelta(days=1)).isoformat()
    d = _get("getCampTR.php", {"camp": st["code"], "dateDeb": deb})
    if not d or not d.get("results"):
        return None
    entete, rows = d["entete"], d["results"]
    row = rows[-1]
    out = {
        "name": st["name"], "code": st["code"], "dist_km": st["dist_km"],
        "time": _pick(entete, row, "date"),
        "hs": _num(_pick(entete, row, "h1/3", "hm0")),        # hauteur significative (m)
        "period": _num(_pick(entete, row, "th1/3", "t. au pic", "t02")),  # période (s)
        "dir": _num(_pick(entete, row, "dir")),               # direction au pic (°)
        "temp": _num(_pick(entete, row, "temp")),             # température mer (°C)
    }
    with open(cpath, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    return out
