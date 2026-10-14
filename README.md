# Surfcast

Prévisions de surf **explicables** : pas seulement « 1,2 m à 9 s », mais *pourquoi* ça
va (ou pas) marcher sur un spot donné. Houle, période, orientation, vent offshore/onshore,
marée, lumière du jour : chaque facteur est noté et expliqué en clair.

Conçu pour les spots de la côte atlantique (Charente-Maritime, Vendée), mais tout se
règle dans `spots.yaml`.

## Fonctionnalités
- **Score par créneau horaire** avec explication (facteurs limitants, type de déferlante,
  shorebreak, propreté du plan d'eau), adapté au niveau (débutant / intermédiaire / confirmé).
- **Marée** : pleines et basses mers interpolées, marnage, vive-eau/morte-eau.
- **Où surfer** : classement des spots par jour, carte Leaflet.
- **Vérité terrain** : un journal de sessions comparé au *hindcast* du modèle, pour savoir
  quel modèle croire sur quel spot.
- **Bouées CANDHIS** (optionnel) : état de mer mesuré en temps réel au large.
- **PWA hors-ligne** : la dernière prévision reste consultable sans réseau sur la plage.
- Données **Open-Meteo** (gratuites, sans clé). Backend Python **stdlib** + PyYAML.

## Architecture
- **Backend Python** (`server.py` + `app/`) : science des vagues, scoring, explications,
  boucle de vérification (hindcast vs sessions réelles).
- **Frontend React** (`frontend/`) : Vite + Tailwind + vite-plugin-pages, alias `@`.
  4 pages : Prévisions, Sessions & vérité terrain, Carte, La science.
- **Image Docker unique** (`Dockerfile`) : front buildé + backend sur le port 8090,
  publiée par la CI sur `ghcr.io/calaxo/surfcast`.

## Lancer en dev
```bash
# 1) Backend (port 8090)
pip install -r requirements.txt
PYTHONUTF8=1 python server.py --port 8090

# 2) Frontend (port 5173, proxy /api -> 8090)
cd frontend
npm install
npm run dev
```
Ouvrir http://localhost:5173

Tests (hors-ligne, stdlib) : `python -m unittest discover -s tests`

## Docker
```bash
docker run -d -p 8090:8090 \
  -v surfcast_cache:/app/cache \
  -v ./sessions.json:/data/sessions.json:ro -e SURFCAST_SESSIONS=/data/sessions.json \
  -e CANDHIS_TOKEN=... \
  ghcr.io/calaxo/surfcast:latest
```
(`CANDHIS_TOKEN` et le volume `sessions.json` sont optionnels.)

## Configuration
| Élément | Rôle |
|---|---|
| `spots.yaml` | spots : orientation, fenêtre de houle, offshore, pente, marée idéale, temps de route depuis `home` |
| `sessions.json` | **votre** journal de sessions (git-ignoré). Partir de `sessions.example.json` |
| `SURFCAST_SESSIONS` | chemin du journal (ex. fichier monté en volume). Défaut : `sessions.json`, sinon l'exemple |
| `CANDHIS_TOKEN` | jeton API CANDHIS (Cerema) pour les bouées. Absent : fonctionnalité désactivée |
| `SURFCAST_STATIC` | dossier du front buildé (défini dans l'image Docker) |
| `cache/` | cache des réponses Open-Meteo (hindcast permanent, prévisions 3 h) |

## Endpoints
- `GET /api/config` : home + spots
- `GET /api/spots` : configuration des spots
- `GET /api/forecast?spot=&model=&level=&past=` : prévision 3 j (+ jours passés, 14 max) :
  évaluations horaires, `daylight` et `tides` par jour
- `GET /api/sessions?model=` : journal + vérification (hindcast vs ressenti) + `energy_by_spot`
- `GET /api/overview?model=&level=` : score du jour par spot (carte)
- `GET /api/ranking?level=` : meilleur créneau par spot et par jour
- `GET /api/buoy?spot=` : bouée CANDHIS la plus proche (si `CANDHIS_TOKEN`)

## Documentation
- `docs/physique-vagues-surf.md` : brief scientifique sourcé (houle, déferlement, marée).
- `docs/etude-rider-report.md` : étude d'un service existant, idées reprises et écartées.
- `web/` : ancienne page HTML standalone, gardée en secours.

## Licence
[MIT](LICENSE) © 2026 calaxo. Réutilisation libre, y compris commerciale, à condition de
conserver la mention de copyright et la licence.
