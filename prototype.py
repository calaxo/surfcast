"""
Prototype CLI : valide la science sur un vrai spot avec les vraies données Open-Meteo.

Usage:
    python prototype.py [spot_key] [--model mfwam|gfs_wave]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from app import sources, science  # noqa: E402


def main():
    spot_key = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "la-bouverie-la-palmyre"
    model = None
    if "--model" in sys.argv:
        model = sys.argv[sys.argv.index("--model") + 1]

    here = os.path.dirname(__file__)
    spots = sources.load_spots(os.path.join(here, "spots.yaml"))
    spot = spots[spot_key]
    print(f"\n=== {spot['name']} ===")
    print(f"orientation plage {spot['beach_facing']}° | fenêtre houle {spot['swell_window']} "
          f"| offshore {spot['offshore_dir']}° | modèle: {model or 'défaut Open-Meteo'}\n")

    hours = sources.merged_hours(spot["latitude"], spot["longitude"], spot["timezone"],
                                 days=3, model=model)

    evals = []
    for h in hours:
        # priorité à la partition "swell" ; fallback sur wave_* global
        sh = h["swell_wave_height"] if h["swell_wave_height"] is not None else h["wave_height"]
        sp = h["swell_wave_peak_period"] if h["swell_wave_peak_period"] is not None else h["wave_period"]
        sd = h["swell_wave_direction"] if h["swell_wave_direction"] is not None else h["wave_direction"]
        c = science.Conditions(
            time=h["time"], swell_h=sh, swell_period=sp, swell_dir=sd,
            wind_wave_h=h["wind_wave_height"], wind_speed=h["wind_speed_10m"],
            wind_dir=h["wind_direction_10m"],
        )
        if c.swell_h is None or c.swell_period is None:
            continue
        evals.append(science.evaluate(c, spot))

    # Résumé par jour : meilleur créneau
    by_day = {}
    for e in evals:
        by_day.setdefault(e.time[:10], []).append(e)

    for day, es in sorted(by_day.items()):
        best = science.best_window(es)
        print(f"── {day} ──  meilleur créneau {best.time[11:16]} : {best.score}/10  ({best.label})")
        print("   " + best.explanation.replace("**", ""))
        print()

    # Détail heure par heure du 1er jour (aperçu)
    print("Aperçu horaire (jour 1) :")
    day1 = sorted(by_day)[0]
    for e in by_day[day1]:
        hh = int(e.time[11:13])
        if hh % 3 != 0:
            continue
        d = e.drivers
        print(f"  {e.time[11:16]}  {e.score:>4}/10  {d['energie']['value']:>5} kW/m  "
              f"H={d['houle']['h']}m T={d['houle']['periode']}s  "
              f"vent {d['vent']['speed']}km/h {d['vent']['label']}")


if __name__ == "__main__":
    main()
