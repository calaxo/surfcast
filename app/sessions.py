"""
Journal de sessions + boucle de vérification.

Idée : pour chaque session loguée à la main (ressenti réel), on récupère ce que le
modèle de houle DISAIT ce jour-là (hindcast via l'API archive Open-Meteo), on le passe
dans le même moteur de score, et on compare au ressenti. Au fil des sessions, ça dit
quel modèle croire sur CE spot et ça confirme/infirme les règles locales.
"""
from __future__ import annotations
import json
import os
import urllib.parse
import urllib.request

from . import science

ARCHIVE_MARINE = "https://marine-api.open-meteo.com/v1/marine"
ARCHIVE_WEATHER = "https://archive-api.open-meteo.com/v1/archive"

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")


def load_sessions(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _get(url: str, params: dict) -> dict:
    qs = urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(f"{url}?{qs}", headers={"User-Agent": "surfcast/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def hindcast_day(lat, lon, tz, date, model=None) -> list[science.Conditions]:
    """Récupère les conditions passées (hindcast). Mis en cache sur disque : les
    données passées ne changent jamais → un seul appel réseau, puis instantané."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    key = f"hindcast_{lat}_{lon}_{date}_{model or 'auto'}.json"
    cpath = os.path.join(CACHE_DIR, key)
    if os.path.isfile(cpath):
        with open(cpath, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return [science.Conditions(**c) for c in raw]

    conds = _fetch_hindcast(lat, lon, tz, date, model)
    if conds:   # ne JAMAIS cacher un résultat vide (sinon un timeout se grave en dur)
        with open(cpath, "w", encoding="utf-8") as f:
            json.dump([c.__dict__ for c in conds], f, ensure_ascii=False)
    return conds


def _fetch_hindcast(lat, lon, tz, date, model=None) -> list[science.Conditions]:
    marine_params = {
        "latitude": lat, "longitude": lon, "timezone": tz,
        "start_date": date, "end_date": date,
        "hourly": "swell_wave_height,swell_wave_peak_period,swell_wave_direction,"
                  "secondary_swell_wave_height,secondary_swell_wave_period,secondary_swell_wave_direction,"
                  "wave_height,wave_period,wave_direction,wind_wave_height,sea_level_height_msl",
    }
    if model:
        marine_params["models"] = model
    weather_params = {
        "latitude": lat, "longitude": lon, "timezone": tz,
        "start_date": date, "end_date": date,
        "hourly": "wind_speed_10m,wind_direction_10m",
    }
    m = w = {}
    for _attempt in range(2):   # l'API archive est capricieuse → 1 retry
        try:
            m = _get(ARCHIVE_MARINE, marine_params).get("hourly", {})
            w = _get(ARCHIVE_WEATHER, weather_params).get("hourly", {})
            break
        except Exception:
            m = w = {}
    if not m.get("time"):
        return []

    out = []
    times = m.get("time", [])
    for i, t in enumerate(times):
        sh = _pick(m, "wave_height", i) or _pick(m, "swell_wave_height", i)
        sp = _pick(m, "wave_period", i) or _pick(m, "swell_wave_peak_period", i)
        sd = _pick(m, "wave_direction", i) or _pick(m, "swell_wave_direction", i)
        if sh is None or sp is None:
            continue
        out.append(science.Conditions(
            time=t, swell_h=sh, swell_period=sp, swell_dir=sd,
            wind_wave_h=_pick(m, "wind_wave_height", i),
            wind_speed=_pick(w, "wind_speed_10m", i),
            wind_dir=_pick(w, "wind_direction_10m", i),
            tide_m=_pick(m, "sea_level_height_msl", i),
            sw1_h=_pick(m, "swell_wave_height", i), sw1_t=_pick(m, "swell_wave_peak_period", i),
            sw1_dir=_pick(m, "swell_wave_direction", i),
            sw2_h=_pick(m, "secondary_swell_wave_height", i),
            sw2_t=_pick(m, "secondary_swell_wave_period", i),
            sw2_dir=_pick(m, "secondary_swell_wave_direction", i),
        ))
    return out


def _pick(hourly, key, i):
    arr = hourly.get(key)
    if not arr or i >= len(arr):
        return None
    return arr[i]


def verify_session(sess: dict, spot: dict, model=None) -> dict:
    """Compare le ressenti loggué au score qu'aurait donné le modèle ce jour-là."""
    conds = hindcast_day(spot["latitude"], spot["longitude"], spot["timezone"],
                         sess["date"], model=model)
    science.annotate_tide(conds)   # remplit tide_norm / tide_trend sur la journée
    result = {"id": sess["id"], "date": sess["date"], "spot": sess["spot"],
              "time_range": sess.get("time_range"),
              "rating_obs": sess["rating"], "verdict_obs": sess["verdict"],
              "observed": sess["observed"], "notes": sess.get("notes", ""),
              "model_available": bool(conds)}
    if not conds:
        result["note_model"] = "Pas de reconstruction modèle dispo pour cette date."
        return result

    evals = [science.evaluate(c, spot) for c in conds]
    # Si la session a une plage horaire (ex "15:00-19:00"), on compare le modèle SUR cette
    # plage — sinon on prend les heures de jour. Indispensable pour les sessions du même
    # jour à des marées différentes (aprem shorebreak vs soir propre).
    h0, h1 = _parse_range(sess.get("time_range"))
    window = [e for e in evals if h0 <= int(e.time[11:13]) <= h1] or evals
    best = max(window, key=lambda e: e.score)
    scores = [e.score for e in window]
    result["time_range"] = sess.get("time_range")
    result["model_best_score"] = best.score
    result["model_mean_score"] = round(sum(scores) / len(scores), 1) if scores else None
    result["model_best_time"] = best.time[11:16]
    result["model_explanation"] = best.explanation
    result["model_wind_dir"] = best.drivers["vent"]["dir"]
    result["model_wind_label"] = best.drivers["vent"]["label"]
    result["model_tide"] = best.drivers["maree"]["state"]
    result["model_breaker"] = best.drivers["maree"]["breaker"]

    # Comparaison ressenti (0-5) vs modèle (0-10) : on compare la MOYENNE sur la plage
    # (plus juste qu'un pic ponctuel pour un ressenti global de session).
    obs10 = sess["rating"] * 2
    ref = result["model_mean_score"] if result["model_mean_score"] is not None else best.score
    result["gap"] = round(ref - obs10, 1)  # >0 : modèle trop optimiste
    result["agreement"] = _agreement(ref, obs10)
    return result


def _parse_range(tr):
    """'15:00-19:00' -> (15, 19). None -> heures de jour (7, 21)."""
    if not tr or "-" not in tr:
        return 7, 21
    a, b = tr.split("-", 1)
    try:
        return int(a[:2]), int(b[:2])
    except ValueError:
        return 7, 21


def _agreement(model10, obs10):
    d = abs(model10 - obs10)
    if d <= 1.5:
        return "d'accord"
    if d <= 3:
        return "écart moyen"
    return "en désaccord"


def learned_insights(data: dict, spots: dict, model=None) -> dict:
    """Vérifie chaque session + agrège une leçon (ex : rôle du vent offshore)."""
    verifs = []
    for s in data.get("sessions", []):
        spot = spots.get(s["spot"])
        if spot:
            verifs.append(verify_session(s, spot, model=model))
    return {"verifications": verifs, "rules": data.get("learned_rules", [])}
