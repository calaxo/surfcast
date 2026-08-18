"""
Fenêtre de lumière surfable : lever/coucher du soleil + crépuscule civil.

On surfe tant qu'on Y VOIT. La lumière utile va du petit jour (aube civile,
soleil à -6°) à la fin du crépuscule civil du soir (soleil à -6° après le coucher).
La durée du crépuscule VARIE avec la saison et la latitude (plus long l'été).

Calcul solaire = algorithme NOAA (élévation du soleil), sans dépendance externe.
On balaie la journée locale minute par minute et on détecte les passages de seuils :
  -0.833° : lever / coucher du soleil (bord supérieur + réfraction)
  -6°     : aube / crépuscule civils (dernière lumière vraiment exploitable)
"""
from __future__ import annotations
import math
from datetime import date as _date, datetime, timedelta


# --- Décalage horaire Europe/Paris sans dépendre de la base tz système (Windows) ---
def _last_sunday(year: int, month: int) -> _date:
    d = _date(year, month, 31)
    while d.month != month:
        d = _date(year, month, d.day - 1)
    return d - timedelta(days=(d.weekday() + 1) % 7)  # recule jusqu'au dimanche


def europe_paris_offset(d: _date) -> int:
    """+2 (CEST) l'été, +1 (CET) l'hiver. Bascule le dernier dimanche de mars/octobre."""
    start = _last_sunday(d.year, 3)   # -> CEST
    end = _last_sunday(d.year, 10)    # -> CET
    return 2 if start <= d < end else 1


def _sun_altitude_deg(dt_utc: datetime, lat: float, lon: float) -> float:
    """Élévation du soleil (deg) pour un instant UTC, méthode NOAA."""
    doy = dt_utc.timetuple().tm_yday
    hour = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
    gamma = 2.0 * math.pi / 365.0 * (doy - 1 + (hour - 12) / 24.0)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
                       - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))
    decl = (0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
            - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
            - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma))
    tst = hour * 60 + eqtime + 4 * lon                  # true solar time (min)
    ha = math.radians(tst / 4.0 - 180.0)                # angle horaire (rad)
    la = math.radians(lat)
    cos_zen = math.sin(la) * math.sin(decl) + math.cos(la) * math.cos(decl) * math.cos(ha)
    cos_zen = max(-1.0, min(1.0, cos_zen))
    return 90.0 - math.degrees(math.acos(cos_zen))


def _fmt(minute_local: int | None) -> str | None:
    if minute_local is None:
        return None
    minute_local %= 1440
    return f"{minute_local // 60:02d}:{minute_local % 60:02d}"


def sun_events(lat: float, lon: float, date_str: str, utc_offset: int | None = None) -> dict:
    """Retourne les instants clés (heure locale 'HH:MM') pour un jour donné.
    date_str = 'YYYY-MM-DD'. utc_offset : si None, calculé pour Europe/Paris."""
    y, m, d = (int(x) for x in date_str.split("-"))
    day = _date(y, m, d)
    off = europe_paris_offset(day) if utc_offset is None else utc_offset

    # élévation minute par minute sur la journée LOCALE
    alt = []
    for minute in range(0, 1440):
        dt_local = datetime(y, m, d) + timedelta(minutes=minute)
        dt_utc = dt_local - timedelta(hours=off)
        alt.append(_sun_altitude_deg(dt_utc, lat, lon))

    def crossings(threshold):
        rise = set_ = None
        for i in range(1, 1440):
            if alt[i - 1] < threshold <= alt[i] and rise is None:
                rise = i
            if alt[i - 1] >= threshold > alt[i]:
                set_ = i
        return rise, set_

    sunrise, sunset = crossings(-0.833)
    dawn, dusk = crossings(-6.0)

    twilight_pm = (dusk - sunset) if (dusk and sunset) else None
    return {
        "date": date_str,
        "utc_offset": off,
        "civil_dawn": _fmt(dawn),      # premier jour exploitable
        "sunrise": _fmt(sunrise),
        "sunset": _fmt(sunset),
        "civil_dusk": _fmt(dusk),      # dernière lumière exploitable
        "twilight_pm_min": twilight_pm,  # minutes de crépuscule après le coucher
        "surf_light": [_fmt(dawn), _fmt(dusk)],  # fenêtre où l'on y voit
    }


def in_light(hhmm: str, events: dict) -> bool:
    """Est-ce que l'heure 'HH:MM' tombe dans la fenêtre de lumière surfable ?"""
    lo, hi = events.get("surf_light", [None, None])
    if not lo or not hi or not hhmm:
        return True
    return lo <= hhmm <= hi


def arrival_time(depart_hhmm: str, drive_min: int | None) -> str | None:
    """Heure d'arrivée à l'eau = départ + temps de route (min)."""
    if not depart_hhmm or drive_min is None:
        return None
    h, m = int(depart_hhmm[:2]), int(depart_hhmm[3:5])
    total = h * 60 + m + int(drive_min)
    return _fmt(total)
