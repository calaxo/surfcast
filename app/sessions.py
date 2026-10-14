"""
Journal de sessions + boucle de vérification.

Idée : pour chaque session loguée à la main (ressenti réel), on récupère ce que le
modèle de houle DISAIT ce jour-là (hindcast via l'API archive Open-Meteo), on le passe
dans le même moteur de score, et on compare au ressenti. Au fil des sessions, ça dit
quel modèle croire sur CE spot et ça confirme/infirme les règles locales.
"""
from __future__ import annotations
import json

from . import science
from .fetch import CACHE, UpstreamError, get_json, make_key

ARCHIVE_MARINE = "https://marine-api.open-meteo.com/v1/marine"
ARCHIVE_WEATHER = "https://archive-api.open-meteo.com/v1/archive"
HINDCAST_TTL = 365 * 24 * 3600   # le passé ne change plus : un appel, puis cache


def load_sessions(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def hindcast_day(lat, lon, tz, date, model=None) -> list[science.Conditions]:
    """Conditions passées (hindcast), via le cache partagé. Un résultat vide n'est jamais
    mis en cache (sinon une panne passagère se graverait en dur)."""
    try:
        raw = CACHE.get(make_key("hindcast", lat=lat, lon=lon, tz=tz, date=date, model=model),
                        HINDCAST_TTL, lambda: _fetch_hindcast_raw(lat, lon, tz, date, model))
    except UpstreamError:
        return []
    return [science.Conditions(**c) for c in raw]


def _fetch_hindcast_raw(lat, lon, tz, date, model=None) -> list[dict]:
    conds = _fetch_hindcast(lat, lon, tz, date, model)
    if not conds:
        raise UpstreamError(f"hindcast vide pour {date}")
    return [c.__dict__ for c in conds]


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
    # get_json réessaie déjà (délai croissant) : l'API archive est capricieuse
    m = get_json(ARCHIVE_MARINE, marine_params).get("hourly", {})
    w = get_json(ARCHIVE_WEATHER, weather_params).get("hourly", {})
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
    # Puissance moyenne (kW/m) sur la plage → sert à apprendre, spot par spot, la plage
    # d'énergie où l'on se régale (l'équivalent du "ça marche à partir de X kJ" des pros,
    # mais calé sur SES sessions au lieu d'être deviné).
    powers = [e.power_kw_m for e in window if e.power_kw_m is not None]
    result["model_power"] = round(sum(powers) / len(powers), 1) if powers else None

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
    return {"verifications": verifs, "rules": data.get("learned_rules", []),
            "energy_by_spot": energy_by_spot(verifs, spots)}


def energy_by_spot(verifs: list, spots: dict) -> list:
    """Plage de puissance (kW/m) des BONNES sessions (≥ 4/5) et des NULLES (≤ 2/5), par spot.
    C'est l'idée "tel spot commence à marcher à X et sature à Y" — mais mesurée sur les
    sessions réelles loguées plutôt que devinée. Avec peu de sessions la plage est large et
    ça se voit (n affiché) ; elle se resserre au fil du journal."""
    acc = {}
    for v in verifs:
        p = v.get("model_power")
        if p is None:
            continue
        a = acc.setdefault(v["spot"], {"good": [], "bad": []})
        if v["rating_obs"] >= 4:
            a["good"].append(p)
        elif v["rating_obs"] <= 2:
            a["bad"].append(p)
    out = []
    for key, a in acc.items():
        spot = spots.get(key, {})
        rng = lambda xs: [min(xs), max(xs)] if xs else None
        out.append({"spot": key, "name": spot.get("name", key),
                    "good": rng(a["good"]), "n_good": len(a["good"]),
                    "bad": rng(a["bad"]), "n_bad": len(a["bad"])})
    return out
