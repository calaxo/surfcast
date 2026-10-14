# Étude de rider.report — ce qu'on prend, ce qu'on laisse (2026-09-09)

Contexte : un jour d'essai gratuit sur **rider.report** (site FR de prévision surf, 3 €/mois),
47 captures d'écran (dossier local `images/`, hors git) + 5 articles de leur blog. But :
**améliorer surfcast**, pas copier un service. Sa version actuelle est validée
(« j'aime bien la version du site comme ça ») : tout ce qui suit s'y **ajoute**.

## 1. Ce que c'est

Un front sur **Open-Meteo** (même source que nous — attribution « Leaflet · EMODnet ·
Protomaps · Open-Meteo » sur leur carte), habillé en 7 « façons » (RR simple / RR complexe /
Windguru / Surfline / Windy / Yadusurf / Ifremer), avec :

- carte Leaflet + heatmaps (Hs, houles 1/2/3, période, énergie kJ, vent avec particules,
  clapot, T° eau, pression avec isobares), couches bathymétrie EMODnet, bouées, webcams ;
- timeline 7 jours avec la **courbe de marée en fond**, curseur « maintenant », lecture animée ;
- fiche spot : coordonnées (pas de nom !), PM/BM heures + hauteurs, marnage, coef, chevrons
  Vague / Vent / Houle / Houle vent / Houle 2 / Houle 3, T° eau, **énergie kJ**, liens
  Surfline / Windy / Windguru / SHOM, « Partager » ;
- **rose houle/vent centrée sur le spot** (flèche bleue = houle, orange = vent, tournent avec
  l'heure) ;
- choix de 6 modèles de houle et 12 modèles de vent ;
- tableau « Windguru » avec ligne Énergie kJ colorée et Note en étoiles ; mode simple avec
  tuiles + suggestion de combinaison (« Shorty ») + horloge de marée ;
- liste « Obs. marine » (bouées : Pierres Noires, Batz, Belle-Île, Noirmoutier, Yeu,
  Cherbourg, Royan) ;
- onboarding en bulles, sauvegarde de spots, suggestion de webcams, paywall.

## 2. Les bonnes idées — et comment les faire MIEUX

| Idée chez eux | Pourquoi c'est bon | Ce qu'on fait chez nous |
|---|---|---|
| Énergie (kJ) en avant | La hauteur seule ne dit rien ; énergie ∝ H²·T | Chip ⚡ kW/m visible sur la carte-jour + **plage d'énergie de tes bonnes sessions par spot, apprise du journal** (eux laissent le lecteur deviner « ça marche à partir de 100 kJ ») |
| Courbe de marée en fond de timeline | Forme de la marée d'un coup d'œil | Courbe **par jour** avec PM/BM, **bande de score horaire dessous**, nuit grisée, **⚠ shorebreak**, « maintenant », **ta session** surlignée → répond à *quand dans la marée*, pas juste *quelle marée* |
| Rose houle/vent centrée spot | Direction lisible instantanément | On ajoute la **géométrie du spot** : terre grisée (`beach_facing`), **fenêtre de houle** (`swell_window`) en arc, **secteur offshore** (`offshore_dir`) en arc → on VOIT si la houle rentre et si le vent est de terre |
| PM/BM + marnage | Base de toute session | Événements interpolés (parabole sur 3 points horaires) depuis `sea_level_height_msl` ; marnage + vive-eau/morte-eau déjà là |
| Flèches de direction partout | Lecture rapide | Flèches dans le tableau horaire |
| « Étalement directionnel » (mer rangée vs chantier) | Concept juste, ignoré des sites grand public | Open-Meteo ne le donne pas → **proxy** : part d'énergie de la mer du vent (H² relatif) + écart de direction entre les 2 trains de houle. Indicateur informatif, hors score tant que non calibré |

## 3. Ce qu'on ne prend PAS (et pourquoi)

- **7 skins** → 7 palettes, 7 logiques, incohérent. L'auteur a fait retirer le sélecteur de modèle
  (« je veux juste surfer ») : une seule bonne vue.
- **12 modèles de vent + 6 de houle** → paralysie du choix. La seule version utile serait un
  indice d'**accord entre modèles** (confiance). Parqué.
- **Heatmaps** → chargement client de 100+ points un par un (« 27/104 », « modèle indisponible
  sur certains points »), lent ; et ça ne répond pas à « quel spot, quelle heure ». Notre carte
  des scores par spot le fait.
- **Échelles arc-en-ciel** → mauvaise dataviz. On garde rouge/jaune/vert sémantiques.
- **Responsive** → boutons du header coupés (sauvegarde à moitié hors écran), onglets de
  variables tronqués des deux côtés (« ue | Houles … S »), toast « Pas de données » sur le
  graphe, attribution Leaflet sur 2 lignes, carte à ~60 % de l'écran et la donnée en dessous,
  bulles d'onboarding empilées, coordonnées en titre au lieu d'un nom.
- **Absence d'interprétation** → marée affichée mais pas de shorebreak ; vent affiché mais pas
  offshore/onshore *relatif au spot* ; énergie affichée mais pas de niveau ; « Note ★★★ » sans
  base visible. **C'est le créneau de surfcast.** On le garde comme colonne vertébrale.
- **Coefficient de marée** → il faut l'unité de hauteur SHOM du port de référence ; le déduire
  du marnage local sans ça, c'est du faux. On affiche marnage + vive-eau/moyenne/morte-eau.

## 4. Vérification scientifique de leurs articles

### « 80 cm à 1,20 m » (Hs vs séries) — ✅ juste
Hs = moyenne du tiers le plus haut, H1/10 ≈ 1,27·Hs, les ~1 % « mutantes » = queue de
Rayleigh. Déjà dans notre page Science.

### Séries = interférence de houles de périodes proches — ✅ juste
= notre viz « modulation AM ». Nuance : « les 1 % plus grosses sont bien plus grosses en longue
période » n'est **pas** un effet Rayleigh (Hmax/Hs ne dépend pas de la période). Ce qui est
vrai : une houle longue **shoale davantage** (Hb ∝ T^0,4) et ses groupes sont plus **marqués**
(spectre étroit).

### Bancs de sable / baïnes — ✅ qualitativement correct, simplifié
Un banc vit quelques semaines ; la marche devant le banc fait un pic identifiable ; la boucle
baïne → banc → baïne s'auto-alimente. Le mécanisme « eau coincée dans les rides du sable » est
une image : le moteur admis est le **gradient longshore de set-up** des vagues (plus d'eau
poussée là où ça casse fort → courants d'alimentation → chenal → renforcement). Conséquence
utile pour nous : **le modèle ne voit pas les bancs** → d'où le journal de sessions et les
webcams.

### Énergie — ❌ erreur significative
Leur vulgarisation « E ∝ H × λ/2 » donne E ∝ H·T², d'où « **1 m à 17 s ≡ 4,5 m à 8 s** » et
« +20 % de période = +44 % d'énergie ».

Physique réelle (eau profonde) :
- densité d'énergie **E = ρ·g·H²/8** → ∝ **H²**, indépendante de T ;
- flux d'énergie (ce qui arrive sur la plage par seconde) **P = E·Cg ∝ H²·T** (Cg = g·T/4π).

Donc 1 m @ 17 s ≡ H @ 8 s avec H²·8 = 17 → **H = 1,46 m**, pas 4,5 m (surestimé ×3). Et
+20 % de période = **+20 %** de flux, pas +44 %.

Recoupement par Komar-Gaughan (hauteur déferlante Hb = 0,56·H₀·(H₀/L₀)^-0,2) :
- 1 m @ 17 s → Hb ≈ 1,90 m ;
- 1,46 m @ 8 s → Hb ≈ 1,90 m (identique : la formule dérive de la conservation du flux) ;
- 4,5 m @ 8 s → Hb ≈ 4,7 m (rien à voir).

Le message de fond (« la période compte autant que la hauteur ») reste vrai ; le chiffre choc
est faux. Notre règle documentée : **P ∝ T** (+10 % par seconde autour de 10 s), **Hb ∝ T^0,4**
(+3-4 %/s).

### Pédagogie par niveau — ✅ raisonnable
Débutant → taille ; intermédiaire → période ; expert → énergie + étalement. Notre score par
niveau (`LEVELS`, `size_fit`, `clean_floor`, `wind_floor`) l'incarne déjà.

## 5. Ce qui a été construit (local, 2026-09-09)

Backend
- `science.py` : `sea_organisation()` (proxy d'étalement directionnel) → `drivers.mer` ;
  `drivers.maree.level` / `.range` (niveau et marnage horaires) ; `drivers.energie.density_kj_m2`.
- `server.py` : `tide_events()` → `/api/forecast` renvoie `tides[date] = {events: [{type PM/BM,
  time, height}], range, amplitude}` (extrema interpolés en parabole sur 3 points horaires).
- `sessions.py` : `model_power` par session + `energy_by_spot` (plage kW/m des sessions ≥ 4/5 vs
  ≤ 2/5) dans `/api/sessions`.

Frontend
- `TideChart.jsx` : courbe de marée du jour + PM/BM + bande de score + nuit + ⚠ shorebreak +
  « maintenant » + session.
- `SpotRose.jsx` : rose du spot (terre, fenêtre de houle, secteur offshore, flèches houle/vent).
- `DayCard.jsx` : bloc marée + rose, chips ⚡ énergie et 〰 mer, tableau horaire enrichi.
- `science.jsx` : sections 8 (énergie kJ vs kW/m, le piège du 4,5 m), 9 (étalement directionnel),
  10 (bancs et baïnes).
- `sessions.jsx` : carte « ton énergie de kiff, spot par spot ».

## 6. Parqué (à discuter)
- Indice d'**accord entre modèles** (MFWAM / GWAM / EWAM) sur le meilleur créneau = confiance.
- Couche **bathymétrie EMODnet** (WMS gratuit) sur la carte, pour lire les fonds.
- **Coefficient de marée** si on renseigne l'unité de hauteur du port de référence par spot.
- Intégrer `drivers.mer` au score une fois quelques sessions « mer croisée » loguées.
