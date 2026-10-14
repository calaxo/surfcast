"""
Récupération des données ouvertes.

Source principale : Open-Meteo (gratuit, sans clé API).
  - Marine API  : houle / mer du vent / période / direction
  - Forecast API: vent 10m (vitesse + direction)

Open-Meteo agrège plusieurs modèles ; on peut demander explicitement
le modèle Météo-France (MFWAM) et comparer avec GFS-Wave.
"""
from __future__ import annotations

from .fetch import CACHE, get_json, make_key

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# Les modèles changent au mieux toutes les heures : 1 h de cache partagé suffit.
FORECAST_TTL = 3600
# Une SEULE requête par (spot, modèle) couvre toutes les vues : on demande toujours
# FETCH_PAST_DAYS jours de passé + FORECAST_DAYS jours de prévision, puis on découpe.
# (avant : une entrée de cache par valeur de `past`, donc 2x plus d'appels)
FETCH_PAST_DAYS = 7
FORECAST_DAYS = 3

MARINE_VARS = [
    "wave_height", "wave_period", "wave_direction",
    "swell_wave_height", "swell_wave_peak_period", "swell_wave_direction",
    # houle SECONDAIRE (2e train, ex : houle de fond longue sous la mer du vent) — MFWAM
    "secondary_swell_wave_height", "secondary_swell_wave_period", "secondary_swell_wave_direction",
    "wind_wave_height", "wind_wave_period",
    "sea_level_height_msl",   # marée (niveau de mer rel. niveau moyen) — sans clé !
    "sea_surface_temperature",  # température de l'eau (°C) → choix de combinaison
]
# temperature_2m / apparent_temperature : l'air et le ressenti comptent autant que l'eau
# pour savoir si on va cailler (on passe le plus clair du temps ASSIS sur la planche,
# torse et tête au vent, pas immergé).
WIND_VARS = ["wind_speed_10m", "wind_direction_10m", "wind_gusts_10m",
             "temperature_2m", "apparent_temperature"]


def fetch_marine(lat: float, lon: float, tz: str, model: str | None = None) -> dict:
    params = {
        "latitude": lat, "longitude": lon, "timezone": tz,
        "hourly": ",".join(MARINE_VARS), "forecast_days": FORECAST_DAYS,
        "past_days": FETCH_PAST_DAYS,
    }
    if model:
        params["models"] = model
    return get_json(MARINE_URL, params)


def fetch_wind(lat: float, lon: float, tz: str) -> dict:
    # Le vent ne dépend pas du modèle de houle : une seule entrée partagée par spot.
    params = {
        "latitude": lat, "longitude": lon, "timezone": tz,
        "hourly": ",".join(WIND_VARS), "forecast_days": FORECAST_DAYS,
        "past_days": FETCH_PAST_DAYS,
    }
    return get_json(FORECAST_URL, params)


def merged_hours(lat: float, lon: float, tz: str, days: int = 3, model: str | None = None,
                 past_days: int = 0) -> list[dict]:
    """Marine + vent fusionnés par heure, découpés sur [aujourd'hui - past_days, +days[.
    Les variables demandées font partie de la clé : en ajouter invalide le cache tout seul."""
    days = max(1, min(int(days), FORECAST_DAYS))
    past_days = max(0, min(int(past_days), FETCH_PAST_DAYS))
    marine = CACHE.get(make_key("marine", lat=lat, lon=lon, tz=tz, model=model,
                                vars=",".join(MARINE_VARS)),
                       FORECAST_TTL, lambda: fetch_marine(lat, lon, tz, model))
    wind = CACHE.get(make_key("wind", lat=lat, lon=lon, tz=tz, vars=",".join(WIND_VARS)),
                     FORECAST_TTL, lambda: fetch_wind(lat, lon, tz))
    return _slice_days(_fetch_merged(marine, wind), FETCH_PAST_DAYS - past_days, days + past_days)


def _slice_days(hours: list[dict], skip: int, keep: int) -> list[dict]:
    dates = sorted({h["time"][:10] for h in hours})
    wanted = set(dates[skip:skip + keep])
    return [h for h in hours if h["time"][:10] in wanted]


def _fetch_merged(marine: dict, wind: dict) -> list[dict]:
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
            "sea_surface_temperature": _at(mh, "sea_surface_temperature", i),
            "wind_speed_10m": _at(wh, "wind_speed_10m", wi) if wi is not None else None,
            "wind_direction_10m": _at(wh, "wind_direction_10m", wi) if wi is not None else None,
            "wind_gusts_10m": _at(wh, "wind_gusts_10m", wi) if wi is not None else None,
            "temperature_2m": _at(wh, "temperature_2m", wi) if wi is not None else None,
            "apparent_temperature": _at(wh, "apparent_temperature", wi) if wi is not None else None,
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
