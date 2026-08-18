"""
Récupération des données ouvertes.

Source principale : Open-Meteo (gratuit, sans clé API).
  - Marine API  : houle / mer du vent / période / direction
  - Forecast API: vent 10m (vitesse + direction)

Open-Meteo agrège plusieurs modèles ; on peut demander explicitement
le modèle Météo-France (MFWAM) et comparer avec GFS-Wave.
"""
from __future__ import annotations
import json
import os
import time
import urllib.request
import urllib.parse

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
FORECAST_TTL = 3 * 3600  # la prévision ne change que quelques fois/jour → cache 3 h

MARINE_VARS = [
    "wave_height", "wave_period", "wave_direction",
    "swell_wave_height", "swell_wave_peak_period", "swell_wave_direction",
    # houle SECONDAIRE (2e train, ex : houle de fond longue sous la mer du vent) — MFWAM
    "secondary_swell_wave_height", "secondary_swell_wave_period", "secondary_swell_wave_direction",
    "wind_wave_height", "wind_wave_period",
    "sea_level_height_msl",   # marée (niveau de mer rel. niveau moyen) — sans clé !
]
WIND_VARS = ["wind_speed_10m", "wind_direction_10m", "wind_gusts_10m"]


def _get_json(url: str, params: dict) -> dict:
    qs = urllib.parse.urlencode(params, doseq=True)
    full = f"{url}?{qs}"
    req = urllib.request.Request(full, headers={"User-Agent": "surfcast/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_marine(lat: float, lon: float, tz: str, days: int = 3, model: str | None = None,
                 past_days: int = 0) -> dict:
    params = {
        "latitude": lat, "longitude": lon, "timezone": tz,
        "hourly": ",".join(MARINE_VARS), "forecast_days": days,
    }
    if past_days:
        params["past_days"] = past_days   # Open-Meteo renvoie passé + prévision d'un coup
    if model:
        params["models"] = model
    return _get_json(MARINE_URL, params)


def fetch_wind(lat: float, lon: float, tz: str, days: int = 3, past_days: int = 0) -> dict:
    params = {
        "latitude": lat, "longitude": lon, "timezone": tz,
        "hourly": ",".join(WIND_VARS), "forecast_days": days,
    }
    if past_days:
        params["past_days"] = past_days
    return _get_json(FORECAST_URL, params)


def merged_hours(lat: float, lon: float, tz: str, days: int = 3, model: str | None = None,
                 past_days: int = 0) -> list[dict]:
    """Fusionne marine + vent par heure. Cache disque TTL pour éviter les appels lents répétés."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cpath = os.path.join(CACHE_DIR, f"forecast_{lat}_{lon}_{days}_{past_days}_{model or 'auto'}.json")
    if os.path.isfile(cpath) and (time.time() - os.path.getmtime(cpath)) < FORECAST_TTL:
        with open(cpath, "r", encoding="utf-8") as f:
            return json.load(f)
    out = _fetch_merged(lat, lon, tz, days, model, past_days)
    with open(cpath, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    return out


def _fetch_merged(lat: float, lon: float, tz: str, days: int = 3, model: str | None = None,
                  past_days: int = 0) -> list[dict]:
    marine = fetch_marine(lat, lon, tz, days, model, past_days)
    wind = fetch_wind(lat, lon, tz, days, past_days)
    mh = marine.get("hourly", {})
    wh = wind.get("hourly", {})
    times = mh.get("time", [])
    wtimes = wh.get("time", [])
    windex = {t: i for i, t in enumerate(wtimes)}

    out = []
    for i, t in enumerate(times):
        wi = windex.get(t)
        out.append({
            "time": t,
            "wave_height": _at(mh, "wave_height", i),
            "wave_period": _at(mh, "wave_period", i),
            "wave_direction": _at(mh, "wave_direction", i),
            "swell_wave_height": _at(mh, "swell_wave_height", i),
            "swell_wave_peak_period": _at(mh, "swell_wave_peak_period", i),
            "swell_wave_direction": _at(mh, "swell_wave_direction", i),
            "secondary_swell_wave_height": _at(mh, "secondary_swell_wave_height", i),
            "secondary_swell_wave_period": _at(mh, "secondary_swell_wave_period", i),
            "secondary_swell_wave_direction": _at(mh, "secondary_swell_wave_direction", i),
            "wind_wave_height": _at(mh, "wind_wave_height", i),
            "wind_wave_period": _at(mh, "wind_wave_period", i),
            "sea_level_height_msl": _at(mh, "sea_level_height_msl", i),
            "wind_speed_10m": _at(wh, "wind_speed_10m", wi) if wi is not None else None,
            "wind_direction_10m": _at(wh, "wind_direction_10m", wi) if wi is not None else None,
            "wind_gusts_10m": _at(wh, "wind_gusts_10m", wi) if wi is not None else None,
        })
    return out


def _at(hourly: dict, key: str, i):
    arr = hourly.get(key)
    if arr is None or i is None or i >= len(arr):
        return None
    return arr[i]


def load_config(path: str) -> dict:
    """Charge spots.yaml complet ({home, spots}). PyYAML si dispo, sinon mini-parseur."""
    try:
        import yaml  # type: ignore
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except ImportError:
        return {"home": None, "spots": _mini_yaml_spots(path)}


def load_spots(path: str) -> dict:
    return load_config(path).get("spots", {})


def _mini_yaml_spots(path: str) -> dict:
    """Parseur minimal pour spots.yaml (évite la dépendance PyYAML en prototype)."""
    spots, cur, key = {}, None, None
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line.strip() or line.strip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            s = line.strip()
            if s == "spots:":
                continue
            if indent == 2 and s.endswith(":"):
                key = s[:-1]
                cur = {}
                spots[key] = cur
                continue
            if indent >= 4 and ":" in s and cur is not None:
                k, _, v = s.partition(":")
                v = v.split("#")[0].strip()
                cur[k.strip()] = _coerce(v)
    return spots


def _coerce(v: str):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        return [_coerce(x) for x in v[1:-1].split(",") if x.strip()]
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        return v
