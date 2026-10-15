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

Tests (hors-ligne, aucun appel réseau) : `pip install pytest pyyaml && python -m pytest`

## Docker
```bash
docker run -d -p 8090:8090 \
  -v surfcast_cache:/app/cache \
  -v ./sessions.json:/data/sessions.json:ro -e SURFCAST_SESSIONS=/data/sessions.json \
  -e SURFCAST_OWNER_KEY=... -e CANDHIS_TOKEN=... \
  ghcr.io/calaxo/surfcast:latest
```
(`CANDHIS_TOKEN`, `SURFCAST_OWNER_KEY` et le volume `sessions.json` sont optionnels.)

## Public / perso
Le site s'utilise **sans compte**. Seules les données personnelles (journal de sessions,
point de départ et temps de route) sont réservées au propriétaire : il saisit une fois sa clé
(`SURFCAST_OWNER_KEY`, au moins 16 caractères) sur `/connexion`, ce qui pose un cookie
HttpOnly signé. Sans clé configurée, ces données ne sont servies à personne. Le service
worker ne met jamais en cache `/api/me`, `/api/sessions`, `/api/login`, `/api/logout`.
Hors-ligne, l'appli installée (PWA) reste en mode propriétaire grâce à la dernière réponse
gardée sur l'appareil (localStorage, effacé à la déconnexion ou dès que le serveur répond
« visiteur »), et le journal reste consultable.

## Sobriété des appels sortants (`app/fetch.py`)
- cache **partagé** entre visiteurs (mémoire + disque `cache/`) : Open-Meteo 1 h, CANDHIS
  30 min, hindcast permanent ; clé normalisée (coordonnées arrondies, modèle en liste fermée) ;
- une seule requête par (spot, modèle) couvre toutes les vues (7 j passés + 3 j de prévision,
  découpés ensuite), et le vent est partagé entre modèles ;
- **une seule requête en vol par clé** : N visiteurs simultanés = 1 appel ;
- débit global borné (seau à jetons), timeout, nouvel essai à délai croissant ; en cas de
  panne, la dernière donnée connue est servie (jusqu'à 48 h) ;
- budget quotidien : Open-Meteo 5 000 appels (conditions : moins de 10 000), CANDHIS 120 (quota 150) ;
- `Cache-Control` : 10 min pour les prévisions, `private, no-store` pour le perso.

## Configuration
| Élément | Rôle |
|---|---|
| `spots.yaml` | spots : orientation, fenêtre de houle, offshore, pente, marée idéale |
| `home.json` | **votre** point de départ et temps de route par spot (git-ignoré), propriétaire seulement. Partir de `home.example.json` |
| `SURFCAST_HOME` | chemin de ce fichier (ex. monté en volume). Défaut : `home.json`, sinon l'exemple |
| `sessions.json` | **votre** journal de sessions (git-ignoré). Partir de `sessions.example.json` |
| `SURFCAST_SESSIONS` | chemin du journal (ex. fichier monté en volume). Défaut : `sessions.json`, sinon l'exemple. Relu à chaud s'il change |
| `SURFCAST_OWNER_KEY` / `SURFCAST_OWNER_KEY_FILE` | clé d'accès du propriétaire (ou fichier qui la contient). Absente : partie perso fermée |
| `CANDHIS_TOKEN` | jeton API CANDHIS (Cerema) pour les bouées. Absent : fonctionnalité désactivée |
| `SURFCAST_STATIC` | dossier du front buildé (défini dans l'image Docker) |
| `cache/` | cache des réponses sources (hindcast permanent, prévisions 1 h, bouées 30 min) |

## Endpoints
- `GET /api/config` : spots (public ; plus de `home`)
- `GET /api/me` : `{owner, home}` (`home` = `{name, latitude, longitude, drive_min}` ; `owner=false`, `home=null` pour un visiteur)
- `POST /api/login` `{"key": ...}` / `POST /api/logout` : accès propriétaire
- `GET /api/spots` : configuration des spots
- `GET /api/forecast?spot=&model=&level=&past=` : prévision 3 j (+ jours passés, 7 max) :
  évaluations horaires, `daylight` et `tides` par jour
- `GET /api/sessions?model=` : **propriétaire seulement** (401 sinon) ; journal + vérification (hindcast vs ressenti) + `energy_by_spot`
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
