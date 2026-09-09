# Surfcast

Prévisions de surf **explicables** (le *pourquoi* des vagues) pour les spots
accessibles en journée depuis le point de départ.

## Architecture
- **Backend Python** (`server.py` + `app/`) : science des vagues, scoring, explications,
  boucle de vérification (hindcast vs sessions réelles). Données Open-Meteo (gratuit).
- **Frontend React** (`frontend/`) : Vite + Tailwind + vite-plugin-pages, alias `@`.
  4 pages : Prévisions, Sessions & vérité terrain, Carte (Leaflet), La science.

## Lancer en dev
```bash
# 1) Backend (port 8090)
cd surfcast
PYTHONUTF8=1 python server.py --port 8090

# 2) Frontend (port 5173, proxy /api -> 8090)
cd surfcast/frontend
npm install       # première fois
npm run dev
```
Ouvrir http://localhost:5173

## Notes
- `cache/` (git-ignoré) : hindcast (permanent) + prévisions (TTL 3 h). L'API archive
  Open-Meteo est lente (~20 s/appel) → le cache est indispensable.
- `spots.yaml` : config des spots (orientation, fenêtre houle, offshore, temps de route).
- `sessions.json` : journal de sessions loguées (vérité terrain).
- `docs/physique-vagues-surf.md` : brief scientifique complet et sourcé.
- `docs/etude-rider-report.md` : étude d'un site concurrent (2026-09) — idées reprises, écartées, erreurs de science relevées.
- `web/` : ancienne page HTML standalone (remplacée par `frontend/`), gardée en secours.

## Références / ce que regardent les pros

Vu récemment un **pro** qui croisait **plusieurs sources** plutôt qu'une seule appli :
- **Windguru** — la référence « données brutes » (modèles GFS/ICON, houle, vent, période) en
  tableau dense. ⭐ Pile la donnée que Surfcast **explique** au lieu de juste l'afficher.
- **Windy** — la **carte animée** (houle, vent, rafales), très visuelle pour voir arriver un train
  de houle et lire l'**offshore** local.
- **« houle »** — probablement **surf-report / Allosurf (houle.org / lasession)** côté FR, ou le
  terme générique ; à préciser.
- **Surfline** — le **premier de la classe** (LOLA swell model, cams, ratings, prévisions longues),
  en grande partie **payant**.

👉 **À en tirer pour Surfcast** : (1) le pro **recoupe des modèles** (GFS vs ICON…) → conforte
l'option `model=` déjà prévue ; (2) ces sites **donnent le chiffre mais pas le *pourquoi*** → c'est
exactement le créneau de Surfcast (« explicable »). Idée : documenter, pour chaque spot, **comment
lire Windguru/Windy** et **où Surfcast apporte l'explication** en plus. (Windguru a une **API**
partielle ; Surfline/Windy ont des API **payantes/limitées** → rester sur **Open-Meteo** comme
source, et se comparer à ces références en validation.)

## Endpoints backend
- `GET /api/config` — home + spots
- `GET /api/forecast?spot=&model=&level=&past=` — prévision 3 j (+ jours passés) : evals horaires (score, drivers, explication), `daylight` et `tides` (PM/BM interpolés, marnage) par jour
- `GET /api/sessions?model=` — journal + vérification (hindcast vs ressenti) + `energy_by_spot` (plage kW/m des bonnes/mauvaises sessions)
- `GET /api/overview?model=` — score du jour par spot (pour la carte)
