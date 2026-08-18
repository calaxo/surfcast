# Physique des vagues de surf — brief scientifique vérifié

> Document de référence pour l'app Surfcast (prévision "explicable").
> Toutes les formules sont vérifiées et sourcées. SI : g = 9,81 m/s², ρ_mer = 1025 kg/m³, H (m), T (s), h (m profondeur), z (m, positif vers le haut, 0 = surface au repos), k = 2π/L (rad/m), ω = 2π/T (rad/s).
> Les blocs ⚠️ **CORRECTION** signalent les affirmations utilisateur fausses/approximatives.

---

## 1. Houle vs mer du vent (sea vs swell)

**Définitions physiques**
- **Mer du vent (wind sea)** : vagues *activement* générées et forcées par le vent *local*. Irrégulières, à crêtes courtes, "clapot", spectre large, faces raides (cambrure H/L élevée), périodes multiples superposées.
- **Houle (swell)** : vagues générées par le vent qui ont *quitté* leur zone de génération et se propagent librement, plus forcées par le vent local. Régulières, à crêtes longues, lisses, spectre étroit, quasi-sinusoïdales, faible cambrure.
- Sources : [Wind wave — Wikipedia](https://en.wikipedia.org/wiki/Wind_wave) · [Swell (wave) — Wikipedia](https://en.wikipedia.org/wiki/Swell_(wave)) · [Sea vs swell — LibreTexts 3.5.4](https://geo.libretexts.org/Bookshelves/Oceanography/Coastal_Dynamics_(Bosboom_and_Stive)/03:_Ocean_waves/3.05:_Wind_wave_generation_and_dispersion/3.5.4:_Sea_versus_swell_waves)

**Transfert d'énergie vent → vagues.** Trois variables de contrôle : **vitesse du vent U**, **fetch** (distance libre sur laquelle le vent souffle) et **durée**. Fetch et durée plus longs → vagues plus hautes ET plus longues (période plus grande).

Deux mécanismes physiques (théorie Miles–Phillips) :
- **Phillips (1957), résonance** : les fluctuations turbulentes de pression atmosphérique pressent la surface ; quand un motif de pression avance à la vitesse d'une vague libre de même longueur, il la force par résonance. Croissance **linéaire en temps** de l'énergie ; domine au tout début (mer plate).
- **Miles (1957), instabilité de cisaillement** : une fois de petites vagues présentes, la perturbation de pression induite dans le profil de vent cisaillé rétroagit sur la vague (transfert concentré à la "couche critique" où U_vent = c_vague). Croissance **exponentielle** ; domine ensuite.
- **Mer pleinement développée** : pour un U donné, état max où l'apport du vent est équilibré par la dissipation (déferlement/moutonnement). Si le vent cesse ou si les vagues dépassent le fetch/durée avant ce plafond → croissance **fetch-limited** (limitée par la distance) ou **duration-limited** (limitée par le temps).
- Sources : [Miles–Phillips mechanism — Wikipedia](https://en.wikipedia.org/wiki/Miles-Phillips_mechanism) · [Sea States — U. Hawai'i](https://manoa.hawaii.edu/exploringourfluidearth/physical/waves/sea-states)

**Pourquoi la houle se trie par période (dispersion fréquentielle).** En eau profonde les vagues sont *dispersives* : c ∝ T et Cg ∝ T (§2). Quand une mer de tempête à spectre large rayonne au loin, **les composantes de plus longue période voyagent le plus vite et arrivent en premier**, suivies des périodes plus courtes → le champ se "trie" en une houle propre, à bande étroite, de plus en plus régulière avec la distance. L'énergie se disperse aussi (angulaire + radiale) → amplitude décroît avec la distance.

**Période comme critère pratique sea/swell** (conventions, pas une frontière physique nette, basées sur la période pic Tp) :
- **Tp < ~10 s** = mer du vent / "windswell" (décroît en quelques centaines de km)
- **~10–13 s** = houle faible/limite (groundswell)
- **> ~14 s** = houle longue distance, puissante (traverse les océans)
- Sources : [The importance of swell period — Surfline](https://www.surfline.com/surf-news/the-importance-of-swell-period/1555)

---

## 2. Relation de dispersion, longueur d'onde, célérité

**Relation de dispersion linéaire (Airy), profondeur quelconque :**
```
ω² = g · k · tanh(k·h)
```
Source : [Airy wave theory — Wikipedia](https://en.wikipedia.org/wiki/Airy_wave_theory) · [Dispersion (water waves) — Wikipedia](https://en.wikipedia.org/wiki/Dispersion_(water_waves))

**Eau profonde (h > L/2, tanh(kh) → 1)** : ω² = g·k.
```
L0 = g·T² / (2π)  ≈ 1,56 · T²     [m]     longueur d'onde
c0 = g·T  / (2π)  ≈ 1,56 · T      [m/s]   célérité de phase (vitesse des crêtes)
Cg = c0 / 2 = g·T/(4π) ≈ 0,78 · T [m/s]   vitesse de groupe (= ½ célérité)
```
**Vérification du coefficient** : g/(2π) = 9,81/6,2832 = **1,5613** → 1,56 confirmé.
Exemples : T=10 s → L0≈156 m, c0≈15,6 m/s (~30 nœuds), Cg≈7,8 m/s. T=12 s → L0≈225 m, c0≈18,7 m/s, Cg≈9,4 m/s.

**Eau peu profonde (h < L/20, tanh(kh) → kh)** : ω² = g·k²·h.
```
c = √(g·h)     [m/s]   — indépendant de T/L ⇒ NON-DISPERSIF
L = T · √(g·h)
Cg = c         (groupe = phase)
```

### Fact-checks

✅ **"longueur d'onde ∝ T²" — CORRECT** (eau profonde) : L0 = (g/2π)·T², proportionnalité exacte au carré de la période.

⚠️ **CORRECTION — "L0 = 1,28 × H × T²" est FAUX.** En théorie linéaire (Airy) **la longueur d'onde ne dépend PAS de la hauteur H** : L dépend uniquement de T et de h (via ω² = g·k·tanh kh). La bonne forme en eau profonde est **L0 = 1,56·T², sans terme H**.
Diagnostic de la confusion :
- le **1,56** a été miscopié en **1,28** ;
- le **×H** est parasite : tout "×H" dans une formule de longueur d'onde est un signal d'erreur (L est indépendant de l'amplitude au premier ordre) ;
- le H a probablement contaminé depuis une formule d'**énergie/puissance**, où la hauteur entre bien — mais en **H²**, pas H : E = (1/8)·ρ·g·H² (énergie), ou P ≈ 0,49·H²·T kW/m (puissance en eau profonde). Le "1,28" ne correspond à aucune constante standard.
- **À mémoriser** : *L0 = 1,56·T² (m), indépendant de la hauteur.*
- Sources : [Airy wave theory — Wikipedia](https://en.wikipedia.org/wiki/Airy_wave_theory) · [Coastal Wiki — shallow-water wave theory](https://www.coastalwiki.org/wiki/Shallow-water_wave_theory)

---

## 3. Énergie, puissance, shoaling, déferlement

### 3.1 Densité d'énergie (indépendante de T)

Deux coefficients, **tous deux corrects**, selon la convention de hauteur (ce n'est pas une erreur amplitude-vs-hauteur) :

**Vague monochromatique (régulière), hauteur H :**
```
E = (1/8) · ρ · g · H²     [J/m²]
```
Dérivation via amplitude a = H/2 : E = ½·ρg·a² = ½·ρg·(H/2)² = ρg·H²/8. Énergie = cinétique + potentielle, chacune (1/16)ρgH².

**Mer aléatoire, hauteur significative spectrale H_m0 = 4·√m0 :**
```
E = ρ·g·m0 = ρ·g·(H_m0/4)² = (1/16) · ρ · g · H_m0²     [J/m²]
```
⚠️ **Le "1/16" de l'utilisateur n'est PAS une erreur** : c'est la forme mer aléatoire / hauteur significative (m0 = H_m0²/16). Le facteur 2 vs 1/8 vient uniquement de la définition H_m0 = 4√m0. **E est indépendant de la période T** (dépend de H² seulement).
Contrôle : H=2 m, eau de mer → E = 0,125·1025·9,81·4 ≈ **5,0 kJ/m²**.
Sources : [Wave power — Wikipedia](https://en.wikipedia.org/wiki/Wave_power) · [CDIP wave measurement](https://cdip.ucsd.edu/m/documents/wave_measurement.html)

### 3.2 Flux d'énergie (puissance) — pourquoi période longue = plus d'énergie

```
P = E · Cg
```
Forme mer aléatoire (constante 0,49) :
```
P = (1/16)·ρg·H_m0² · (gTe/4π) = (ρ·g²/(64π)) · H_m0² · Te     [W/m]
```
**Vérification de la constante** : ρg²/(64π) = 1025·9,81²/(201,06) ≈ **490,6 W/m ≈ 0,49 kW/m**.
```
P ≈ 0,49 · H_m0² · Te     [kW/m]   (H en m, Te en s)   → P ∝ H² · T
```
(Wikipedia arrondit à ~0,5 kW/m·s ; forme monochromatique = ρg²/(32π) ≈ 0,98, le double, cohérent avec 1/8 vs 1/16.)
Contrôles : H=2 m, Te=12 s → P≈23,5 kW/m ; grosse houle atlantique H=4 m, T=15 s → P≈118 kW/m.
Source : [Wave power — Wikipedia](https://en.wikipedia.org/wiki/Wave_power)

### 3.3 Shoaling (levée) — pourquoi période longue → vague déferlante plus grosse

**Conservation du flux d'énergie le long d'un rayon** (sans réfraction) :
```
E · Cg · b = constante        (b = espacement des rayons)
```
Quand h diminue, **Cg diminue → E (donc H) doit augmenter** près de la côte = shoaling.
```
Coefficient de shoaling :  Ks = H / H0 = √(Cg0 / Cg)
```
**Mécanisme réel du "période longue → plus gros"** : période plus longue ⇒ L0 = gT²/2π plus grand ⇒ la vague "sent le fond" (h < L/2) **plus tôt et en eau plus profonde** ⇒ shoaling sur une distance plus longue ⇒ elle déferle en eau plus profonde hb ⇒ **Hb plus grand** (via Hb = γb·hb, §3.5). Formalisé : à H0 fixé, **Hb ∝ T^(2/5)**.
Source : [Wave shoaling — Wikipedia](https://en.wikipedia.org/wiki/Wave_shoaling)

### 3.4 Indice de hauteur au déferlement (breaker height index) — Komar & Gaughan (1972)

```
Hb / H0' = 0,56 · (H0' / L0)^(−1/5)     ✅ coefficient 0,56 et exposant −1/5 VÉRIFIÉS
```
Forme dimensionnelle équivalente : **Hb = 0,39 · g^(1/5) · H0'^(4/5) · T^(2/5)** (coefficient empirique k=0,39 du papier ; H0' = hauteur large corrigée de la réfraction). Comparaison ancienne : Munk (1949) Hb/H0 = 0,3·(H0/L0)^(−1/3), moins précise.
Sources : [Komar & Gaughan 1972 — ICCE](https://icce-ojs-tamu.tdl.org/icce/index.php/icce/article/view/2763) · [USACE CEM Part II ch.4](https://coastalengineeringmanual.tpub.com/Part-II-Chap4/Part-II-Chap40005.htm)

### 3.5 Indice de profondeur au déferlement (breaker depth index)

```
γb = Hb / hb ≈ 0,78     (McCowan 1891, limite onde solitaire, fond horizontal)
```
0,78 = première estimation standard ; **dépend en réalité de la pente et de la cambrure** (Weggel 1972), fourchette réelle **γb ≈ 0,6–1,2** (jusqu'à ~1,4 en pente forte : γb = 1,40 − 6,85·m pour pente m<0,07). Profondeur de déferlement pratique : **hb = Hb/γb** (une vague de 2 m déferle par ≈2,6 m d'eau).
Sources : [USACE CEM Part II ch.4](https://coastalengineeringmanual.tpub.com/Part-II-Chap4/Part-II-Chap40005.htm) · [LibreTexts 5.2.5 Wave breaking](https://geo.libretexts.org/Bookshelves/Oceanography/Coastal_Dynamics_(Bosboom_and_Stive)/05:_Coastal_hydrodynamics/5.02:_Wave_transformation/5.2.5:_Wave_breaking)

### 3.6 ⚠️ CORRECTION — la règle "+1 s de période → +~20 % de hauteur déferlante" est FAUSSE (trop haute)

À H0' fixé, Komar-Gaughan donne **Hb ∝ T^(2/5) = T^0,4**. Calcul réel de l'augmentation par +1 s :

| Passage | (rapport)^0,4 | ΔHb réel |
|---|---|---|
| 10 → 11 s | 1,100^0,4 = 1,039 | **+3,9 %** |
| 12 → 13 s | 1,083^0,4 = 1,033 | **+3,3 %** |
| 14 → 15 s | 1,071^0,4 = 1,028 | **+2,8 %** |

**Le vrai chiffre est ~+3 à +4 % de hauteur déferlante par +1 s** (autour de T=10–14 s), pas +20 %.
Origine de l'intuition +20 % : elle **confond l'ÉNERGIE/PUISSANCE de la houle au large** (P ∝ H²·T, linéaire en T, +8 % par +1 s à T=12, et bien plus si on compte trains plus longs + décroissance plus lente des longues périodes) avec la **hauteur déferlante** (qui ne croît qu'en T^0,4). Longue période = beaucoup plus d'énergie livrée, mais la hauteur au pic ne gagne que ~3–4 %/s.
Sources : [Komar & Gaughan 1972](https://icce-ojs-tamu.tdl.org/icce/index.php/icce/article/view/2763) · [Wave power — Wikipedia](https://en.wikipedia.org/wiki/Wave_power)

---

## 4. Types de déferlement & nombre d'Iribarren

**Nombre d'Iribarren (surf similarity parameter, breaker parameter) :**
```
ξ = tan(β) / √(H / L0)
```
tan(β) = pente du fond ; H/L0 = cambrure en eau profonde ; L0 = gT²/2π ≈ 1,56·T². **Deux versions** : ξ0 (H = H0 au large) et ξb (H = Hb au déferlement) — seuils différents. Longue période → grand L0 → petite cambrure H/L0 → **ξ plus grand** (pousse vers plongeante/gonflante).

**Seuils exacts (Battjes 1974) — VÉRIFIÉS :**

| Type | ξ0 (eau profonde) | ξb (au déferlement) |
|---|---|---|
| **Glissante** (spilling) | ξ0 < 0,5 | ξb < 0,4 |
| **Plongeante** (plunging) | 0,5 < ξ0 < 3,3 | 0,4 < ξb < 2,0 |
| **Gonflante/frontale** (surging/collapsing) | ξ0 > 3,3 | ξb > 2,0 |

⚠️ Les deux jeux de seuils (0,5/3,3 vs 0,4/2,0) sont souvent confondus dans les sources vulgarisées — ce n'est PAS un désaccord, c'est la distinction large vs déferlement. Toujours préciser la version.
Sources : [Iribarren number — Wikipedia](https://en.wikipedia.org/wiki/Iribarren_number) · [Coastal Wiki — Surf similarity parameter](https://www.coastalwiki.org/wiki/Surf_similarity_parameter) · [USACE CEM Part II ch.4](https://coastalengineeringmanual.tpub.com/Part-II-Chap4/Part-II-Chap40005.htm)

**Description physique**
- **Glissante** : pente douce + vagues raides (courte période) → ξ faible. Déferle progressivement sur plusieurs longueurs d'onde, mousse qui glisse sur la face, pas de tube. Favorisée par vent onshore.
- **Plongeante** : LE tube/rouleau. Fond plus raide (récif/banc/ledge) et/ou houle longue à faible cambrure → ξ intermédiaire. La crête se verticalise, s'enroule et plonge sur le creux au-dessus d'une poche d'air ; libération d'énergie violente et concentrée. Favorisée par vent offshore (tient la lèvre).
- **Gonflante/frontale** : plage raide + houle longue très peu cambrée → ξ élevé. La vague monte/descend le talus sans vrai déferlement, crête lisse peu écumeuse, plage réfléchissante (>50 % d'énergie réfléchie).

**Les beaux tubes = PLONGEANTE**, favorisée par **pente raide (récif/point/beach steep)** ET **houle longue à faible cambrure** (petit H/L0). Les deux augmentent ξ = tanβ/√(H/L0). D'où : récifs/points + houle longue période = barrels propres ; plage sableuse douce + windswell courte = déferlement mou (spilling).

Relations connexes gouvernées par ξ (Battjes, via Coastal Wiki) : indice de déferlement γ ≈ 1,06 + 0,14·ln ξ ; réflexion Cr ≈ 0,1·ξ² (ξ<2,5) ; run-up R ≈ Hs·ξ (0,1<ξ<2,3). Limite de cambrure Miche : (H/L)max = 0,142·tanh(kd), eau profonde → **0,142 ≈ 1/7** (moutonnement).
Sources : [Breaking wave — Wikipedia](https://en.wikipedia.org/wiki/Breaking_wave) · [Miche criterion — Wikipedia](https://en.wikipedia.org/wiki/Miche_criterion) · [Surf Simply — why & how waves break](https://surfsimply.com/magazine/why-and-how-waves-break)

---

## 5. Effet de la marée

**Mécanisme 1 — la marée change la profondeur h → déplace le point de déferlement.** Le déferlement bathymétrique se fixe là où h ≈ Hb/γb. Marée montante → le contour "h ≈ Hb/γb" se déplace **vers la côte** (vagues déferlent plus près) ; marée basse → point de déferlement **vers le large**.

**Mécanisme 2 — la vague "sent" une pente locale différente → ξ change → type de déferlement change.** Sur un profil réel (non plan), déplacer le point de déferlement met la vague au-dessus d'une bathymétrie de tan(β) différent. Comme ξ = tanβ/√(H/L0), la **même houle** peut donner glissante à une marée et plongeante à une autre, uniquement parce que le point de déferlement est sur une partie plus ou moins raide du profil. C'est la raison physique du changement de caractère d'un spot dans la marée.

**Pourquoi certains spots marchent à une marée précise :**
- **Trop d'eau (haute mer sur un banc/récif)** : h > Hb/γb avant le banc → la vague ne "sent" pas le fond → vagues grasses, lentes, molles ("fat", backs off).
- **Trop peu d'eau (basse mer)** : point de déferlement sur le banc/récif peu profond, pente locale raide → vagues creuses, rapides, plongeantes ; mais si trop peu profond → closeout, vidange, cailloux/récif exposés (danger).
- **Mi-marée / marée montante** : point de déferlement pile sur la crête du banc ou le ledge du récif où le profil se raidit optimalement → meilleure forme. La plupart des **beach breaks marchent mieux à mi-marée sur une marée poussante (montante)** ; montante préférée à descendante (l'eau qui pousse ajoute énergie/organisation). Les récifs demandent souvent assez d'eau (montante/haute) pour couvrir le récif.

**Mécanisme 3 — interaction houle/bathymétrie** : shoaling (h↓ → H↑ jusqu'au critère de déferlement), et **réfraction/focalisation** des rayons sur récifs/bancs qui concentrent l'énergie ; la marée module le contraste de profondeur que la houle réfracte.

**Distinction claire houle au large vs vague transformée :**
- **Houle au large (eau profonde, h > L0/2)** : caractérisée par **Hs, Tp, direction** ; quasi indépendante du fond, **insensible à la marée locale** ; c'est ce que reportent bouées et modèles. La cambrure Hs/L0 y fixe le *potentiel* de type de déferlement.
- **Vague transformée près du bord (peu profonde, depth-limited)** : façonnée par **h locale (marée), pente tanβ, réfraction/shoaling** ; hauteur plafonnée par Hb ≈ γb·h, type fixé par ξ avec la pente *locale*. Même Hs/Tp/direction → surf totalement différent selon spot et marée. **Le nombre d'Iribarren est le pont** : il combine la propriété large (H0/L0) et le fond local (tanβ).
Sources : [Surfline — tides & surfing](https://www.surfline.com/surf-news/tides-and-surfing/1107) · [LibreTexts 5.2.5](https://geo.libretexts.org/Bookshelves/Oceanography/Coastal_Dynamics_(Bosboom_and_Stive)/05:_Coastal_hydrodynamics/5.02:_Wave_transformation/5.2.5:_Wave_breaking)

---

## 6. Mouvement orbital sous l'eau

Convention : z positif vers le haut, z=0 en surface, z=−h au fond ; amplitude a = H/2 ; k = 2π/L.

**Profondeur quelconque — orbites elliptiques, demi-axes :**
```
Demi-axe horizontal :  A = (H/2) · cosh[k(z+h)] / sinh(k·h)
Demi-axe vertical   :  B = (H/2) · sinh[k(z+h)] / sinh(k·h)
```
cosh ≥ sinh ⇒ A ≥ B : **ellipses aplaties horizontalement**, de plus en plus avec la profondeur. Au fond (z=−h) : sinh(0)=0 ⇒ **B=0 (aucun mouvement vertical)**, A = (H/2)/sinh(kh) ≠ 0 ⇒ **va-et-vient purement horizontal sur le fond**. Cette vitesse orbitale près du fond entraîne **shoaling, réfraction, friction de fond, déferlement bathymétrique**.

**Eau profonde (kh → ∞) — orbites circulaires, décroissance exponentielle :**
```
A = B = (H/2) · e^(k·z)     (z ≤ 0 ⇒ e^(kz) ≤ 1)
```
Cercles fermés dont le rayon décroît comme **e^(kz)**.
**Vérification "base des vagues" à z = −L/2** : kz = (2π/L)·(−L/2) = **−π**, donc e^(−π) = **0,0432 ≈ 4,3 %**. À une demi-longueur d'onde de profondeur, le rayon orbital ≈ 4 % de sa valeur en surface → négligeable. (À z=−L/4 : e^(−π/2)=21 % ; à z=−L : e^(−2π)=0,2 %.)
Sources : [Airy wave theory — Wikipedia](https://en.wikipedia.org/wiki/Airy_wave_theory) · [Swell (wave) — Wikipedia](https://en.wikipedia.org/wiki/Swell_(wave)) · [LibreTexts 5.4.1 orbital velocities](https://geo.libretexts.org/Bookshelves/Oceanography/Coastal_Dynamics_(Bosboom_and_Stive)/05:_Coastal_hydrodynamics/5.04:_Wave_orbital_velocity_pressure_and_bed_shear_stress/5.4.01:_Wave_orbital_velocities)

---

## 7. Groupes de vagues / sets

✅ **Le modèle mental "modulation AM (porteuse + enveloppe)" est CORRECT.**
Somme de deux sinusoïdes de fréquences proches (identité produit-somme) :
```
cos(k1·x − ω1·t) + cos(k2·x − ω2·t)
   = 2 · cos[(Δk·x − Δω·t)/2] · cos[(k̄·x − ω̄·t)/2]
```
avec k̄=(k1+k2)/2, ω̄=(ω1+ω2)/2, Δk=k1−k2, Δω=ω1−ω2.
- Facteur lent cos[(Δk·x−Δω·t)/2] = **enveloppe / battement** (basse fréquence).
- Facteur rapide cos[(k̄·x−ω̄·t)/2] = **porteuse** (fréquence moyenne).
- Exactement une modulation d'amplitude (radio AM) : porteuse rapide dont l'amplitude est modulée lentement par l'enveloppe.

**Vitesse de groupe vs vitesse de phase — pourquoi les vagues arrivent en séries :**
```
Phase (crêtes)  : c  = ω/k
Groupe (énergie): Cg = dω/dk
Eau profonde : ω = √(g·k) ⇒ c = √(g/k),  Cg = ½√(g/k) = c/2
```
**En eau profonde Cg = c/2** : les crêtes vont **deux fois plus vite** que le groupe — elles apparaissent à l'arrière du groupe, culminent au centre, disparaissent à l'avant. L'énergie (donc les **sets**) se propage à Cg, pas à c → les vagues arrivent en **groupes/séries**.

**Ondes longues liées / surf beat / infragravitaires** (bande ~0,005–0,04 Hz, périodes ~25 s à ~5 min) : sous un **groupe de grandes vagues**, la contrainte de radiation plus forte **abaisse le niveau moyen sous la partie haute du groupe (set-down)** → onde longue "liée", verrouillée au groupe, en opposition de phase avec l'enveloppe. Au déferlement, elle est **libérée en onde infragravitaire libre** (vitesse √(g·h)), se réfléchit sur la plage → observée comme **"surf beat"**.
Sources : [Group velocity — Wikipedia](https://en.wikipedia.org/wiki/Group_velocity) · [Infragravity wave — Wikipedia](https://en.wikipedia.org/wiki/Infragravity_wave) · [Coastal Wiki — Infragravity waves](https://www.coastalwiki.org/wiki/Infragravity_waves)

---

## 8. Distribution statistique des hauteurs — Rayleigh

✅ **Loi de RAYLEIGH — PAS normale, PAS Poisson, PAS exponentielle** (Longuet-Higgins 1952), avec la distinction cruciale :
- **L'élévation de surface η(t)** (niveau autour de la moyenne) est **gaussienne/normale** (somme de nombreuses composantes à phase aléatoire, TCL), variance = m0.
- **Les HAUTEURS H** (crête-à-creux) dans une mer à **bande étroite** sont **Rayleigh**. (L'énergie H² est, elle, exponentielle.)
```
pdf :  p(H) = (2H / Hrms²) · exp[ −(H/Hrms)² ]
CDF :  P(H≤h) = 1 − exp[ −(h/Hrms)² ]
```

**Ratios vérifiés (Rayleigh, bande étroite ; Hrms = hauteur quadratique moyenne) :**

| Grandeur | Formule | Valeur |
|---|---|---|
| Hauteur moyenne | H_moy = (√π/2)·Hrms | **0,886·Hrms** |
| Hauteur significative | Hs = H_1/3 = 1,416·Hrms | **1,416·Hrms** |
| H_moy / Hs | 0,886/1,416 | **0,626** |
| Tiers supérieur → Hs | | Hs = H_1/3 |
| Dixième supérieur | H_1/10 = 1,27·Hs = 1,80·Hrms | **1,27·Hs** ✅ |
| Centième supérieur | H_1/100 = 1,67·Hs = 2,36·Hrms | **1,67·Hs** ✅ (théorique Rayleigh ; CoastalWiki donne 1,52 pour un modèle non-linéaire observé) |

⚠️ **Précision sur la note utilisateur** : H_moy = **0,886·Hrms** (pas 0,626·Hrms). Le **0,626 est H_moy/Hs**. Les deux sont justes, dénominateurs différents.

**Maximum sur N vagues :**
```
H_max (le plus probable) ≈ Hrms·√(ln N)
En unités Hs :  H_max/Hs ≈ 0,707·√(ln N)      ✅ (forme confirmée)
Valeur espérée : E[H_max]/Hrms ≈ √(ln N) + 0,5772/(2√(ln N))   (terme d'Euler)
```
Vérifications numériques (plus probable) :
- **N=1000** : ln N=6,908, √=2,628 → H_max/Hs = 0,706×2,628 = **1,86** (concorde CEM : "H_max = 1,86·H_1/3 pour 1000 cycles").
- **N=3000** : ln N=8,006, √=2,830 → H_max/Hs = **2,00**.
- ⇒ **H_max ≈ 1,86–2,0·Hs pour N≈1000–3000** (un enregistrement de tempête de ~3 h à Tz≈10 s ⇒ N≈1080 vagues). La valeur espérée (terme d'Euler) monte à ~1,9–2,05.

**Lien spectral :**
```
Hs ≈ Hm0 = 4·√m0 = 4·σ     (m0 = variance = aire sous le spectre, σ = écart-type de l'élévation)
```
Cohérent : Hrms = √8·√m0 = 2,83√m0, et Hs = 1,416·Hrms = 4,0√m0. ✅
Sources : [Longuet-Higgins 1952](https://elischolar.library.yale.edu/journal_of_marine_research/774/) · [USACE CEM Part II ch.1](https://coastalengineeringmanual.tpub.com/Part-II-Chap1/Part-II-Chap10080.htm) · [Coastal Wiki — Statistical description](https://www.coastalwiki.org/wiki/Statistical_description_of_wave_parameters) · [Significant wave height — Wikipedia](https://en.wikipedia.org/wiki/Significant_wave_height)

---

## 9. Densité spectrale / spectre directionnel

**Spectre S(f)** = densité de variance (énergie) par bande de fréquence, unités **m²/Hz**. Moments spectraux :
```
mn = ∫₀^∞ f^n · S(f) df
m0 = ∫ S(f) df = variance = σ²         (aire sous le spectre)
Tp = 1/fp     (fp = fréquence du pic = bande la plus énergétique)
T_m01 = m0/m1     T_m02 = √(m0/m2)  (période de passage par zéro)
Hm0 = 4√m0
```

**Spectre directionnel S(f,θ)** = énergie par fréquence ET par direction ; S(f) = ∫ S(f,θ) dθ. Lecture de l'origine de la houle :
- **Pic étroit en θ + pic étroit en f = houle propre (groundswell)** d'une seule tempête lointaine (la dispersion a trié les fréquences, le long trajet a resserré l'étalement directionnel).
- **Large/étalé en θ et f = mer du vent locale** ou sources multiples (fetch court, multi-directions).
- En pratique : pic net basse fréquence (longue période) et directionnel = houle organisée longue distance ; tache large = windswell/mers croisées.

**JONSWAP vs Pierson–Moskowitz :**
- **Pierson–Moskowitz (PM)** = mer **pleinement développée** (équilibre avec le vent) :
  ```
  S(ω) = (α·g²/ω⁵)·exp[−β·(ω0/ω)⁴],   α≈0,0081, β=0,74, ω0=g/U19,5
  ```
- **JONSWAP** = mer **fetch-limited** (mer du Nord) = PM × facteur de rehaussement de pic (pic plus étroit et plus haut) :
  ```
  S(ω) = 155·(H1/3²/(T1⁴·ω⁵))·exp(−944/(T1⁴·ω⁴)) · γ^Y
  γ = 3,3 (typique ; γ=1 redonne PM)
  Y = exp[ −((0,191·ω·T1 − 1)/(√2·σ))² ],   σ=0,07 si ω≤ωp, 0,09 sinon
  ```
  γ^Y vaut γ au pic et →1 dans les ailes (ne raidit que le pic).
Sources : [Wind wave spectrum — Wikipedia](https://en.wikipedia.org/wiki/Wind_wave_spectrum) · [Pierson–Moskowitz spectrum — Wikipedia](https://en.wikipedia.org/wiki/Pierson%E2%80%93Moskowitz_spectrum)

---

## 10. Workflow des prévisionnistes experts — checklist actionnable

1. **Report tout fait → tendance.** Prévision agrégée pour le sens (montée/baisse, gamme de taille, fenêtre de vent) : Surfline, Windguru, Windy, wisuki, surf-report.com, allosurf.net. Anchor, mais on vérifie le *pourquoi* ensuite.
2. **Cartes de pression MSLP (naissance de la houle).** Repérer la **dépression** atlantique dont le champ de vent (fetch) génère la houle. **Anticyclone = air calme → vent local faible/offshore** (surface propre) mais pas de houle. Lectures clés : **espacement des isobares = force du vent** (gradient de pression ; serrées=fort), vent le long des isobares (Coriolis, antihoraire autour d'une dépression NH). Règle stormsurf : chercher **vent >25 kt vers la côte pendant >24 h**, dans la **fenêtre de houle** du spot. Suivre la dépression (T+0/+24/+48) pour viser le fetch.
3. **Cartes de période/énergie + sorties de modèle** (Hs, Tp, direction). **Longue période (12–20+ s) = groundswell** organisé, puissant, réfracte/focalise sur récifs/points. **Courte période (4–9 s) = windswell** désorganisé, décroît vite. Vitesse de propagation ≈ **1,5×Tp en nœuds** → temps de trajet = distance(nm)/vitesse. Lire les champs partitionnés (mer du vent vs houle primaire/secondaire), pas seulement le Hs total.
4. **Croiser prévision vs BOUÉES temps réel (houlographes).** Comparer Hs, Tp, direction prévus vs mesurés. Surveiller les **bouées en amont (au large/up-swell)** : elles enregistrent l'énergie longue période des heures avant la côte, confirment l'heure d'arrivée et la vraie taille. Période qui monte par paliers = dispersion = houle réelle en route.
5. **Webcams.** Vérité terrain que les modèles ne donnent pas : taille réelle qui casse, interaction avec le banc/récif, état de marée, texture (glassy vs bumpy), foule.
6. **Spectre directionnel / densité spectrale.** Finition experte : le spectre 2D (énergie vs fréquence×direction, bouées ou modèle) **sépare trains de houle multiples + mer du vent** qu'un couple Hs/Tp masque. Chaque pic → période + direction → tempête d'origine → quel train allumera le spot (angle d'approche correct).

### Sources de données — France Atlantique / Golfe de Gascogne

Le **Golfe de Gascogne** est l'une des fenêtres de houle les plus énergétiques d'Europe (face WNW–NW au rail des tempêtes nord-atlantiques ; bouée Oléron a mesuré des vagues individuelles ~18 m).

| Source | Type | Fournit | URL |
|---|---|---|---|
| **CANDHIS (Cerema)** | Bouées houlographes in-situ FR (temps réel + archive) | ~30 stations Datawell directionnelles : Hs, Tp, période/direction moyennes, **spectres directionnels**. Atlantique : Belle-Île (05602), Oléron, Le Croisic, Les Landes/Biscarrosse, Gascogne | https://candhis.cerema.fr/ (carte : /_public_/cartes.php) |
| **Copernicus Marine (CMEMS) — IBI Wave** | Modèle régional Iberia-Biscay-Ireland (base MFWAM), forecast+hindcast | ~1/36° (2–3 km), 2×/j, horaire à +10 j ; Hs/période/direction pour spectre total + mer du vent + houle primaire/secondaire ; assimile altimètre + spectres CFOSAT | https://data.marine.copernicus.eu/product/IBI_ANALYSISFORECAST_WAV_005_005/description |
| **CMEMS — Global Waves (MFWAM)** | Modèle global opérationnel | 1/12° (~8 km), analyse + prévi 10 j, 3-horaire ; Hs/Tp/dir + partition houle/mer du vent ; sortie spectrale | https://data.marine.copernicus.eu/product/GLOBAL_ANALYSISFORECAST_WAV_001_027/description |
| **Météo-France MFWAM** | Modèle **spectral 3e génération (WAM)** derrière CMEMS/SHOM | Résout le bilan d'**action des vagues** ; spectre 24 directions × 30 fréquences (0,035–0,58 Hz) ; global 1/12°, vents ECMWF ; côte = nesting WaveWatch III grilles non structurées (10 km → 200–400 m) | via CMEMS ; couche SHOM : https://data.shom.fr |
| **NOAA WaveWatch III (WW3)** | Modèle **spectral 3e génération** US (global+régional) | Bilan d'action-densité (génération vent + interactions non-linéaires 4 vagues + dissipation moutonnement/fond) ; global 0,25–0,5° + grilles imbriquées ; GRIB libre | https://polar.ncep.noaa.gov/waves/ |
| **SHOM — marées** | Prédictions de marée officielles FR | Tables 1 an à l'avance, ~1000 ports : heures/hauteurs PM/BM + coefficients ; marée en tout point. Entrée **marée** du timing surf | https://maree.shom.fr/ |
| **SHOM — portail données** | Bathymétrie, courants, niveau mer | **Bathymétrie** (réfraction/shoaling sur bancs/récifs), atlas de courants, marégraphes REFMAR (surcote vs prédit), couches GRIB MFWAM | https://data.shom.fr |
| **Stormsurf** | Tutoriels + cartes (méthodologie) | Workflow 13 étapes "Create Your Own Surf Forecast" (ID tempête → fetch → table de période → temps de trajet → décroissance), glossaire | https://www.stormsurf.com/page2/papers/papers.shtml |
| **CDIP / NDBC** (analogues US) | Bouées in-situ US | Pas pour la France, mais référence d'affichage de **spectres directionnels** de bouée | https://cdip.ucsd.edu · https://www.ndbc.noaa.gov |

**Note modèles** : MFWAM et WW3 sont tous deux **spectraux 3e génération** — ils ne suivent pas des vagues individuelles mais font évoluer le spectre 2D d'énergie E(f,θ) via l'équation de bilan d'action (vent + interactions non-linéaires + dissipation moutonnement/friction/réfraction). Cette sortie spectrale est exactement ce que lit l'étape 6, et c'est pourquoi le croisement bouée↔modèle de l'étape 4 fonctionne (même langage spectral).

---

## Récapitulatif des corrections aux affirmations utilisateur

| Affirmation utilisateur | Verdict | Correction |
|---|---|---|
| "longueur d'onde ∝ T²" | ✅ CORRECT | L0 = 1,56·T² (m), eau profonde |
| "L0 = 1,28 × H × T²" | ❌ FAUX | L0 = **1,56·T²**, sans H. "1,28" = 1,56 corrompu ; "×H" parasite (contamination d'une formule d'énergie en H²) |
| E = (1/16)·ρ·g·H² | ✅ CORRECT (avec réserve) | Valable pour H = H_m0 (mer aléatoire) ; forme monochromatique = (1/8)·ρ·g·H². Les deux justes. E indépendant de T |
| P ∝ H²·T | ✅ CORRECT | P ≈ 0,49·H_m0²·Te kW/m |
| Hb/H0 = 0,56·(H0/L0)^(−1/5) | ✅ CORRECT | Komar & Gaughan 1972, exposant −1/5, coeff 0,56 |
| γb ≈ 0,78 | ✅ CORRECT | McCowan ; fourchette réelle 0,6–1,2 selon pente/cambrure |
| "+1 s période → +~20 % hauteur déferlante" | ❌ FAUX (trop haut) | Réel ≈ **+3–4 %/s** (Hb ∝ T^0,4). Le +20 % appartient à l'ÉNERGIE (P ∝ T), pas à la hauteur déferlante |
| Modèle AM (porteuse + enveloppe) pour les sets | ✅ CORRECT | Somme de 2 sinus = porteuse × enveloppe ; sets car Cg = c/2 |
| Distribution des hauteurs = Rayleigh | ✅ CORRECT | Rayleigh pour les hauteurs (bande étroite) ; l'élévation, elle, est gaussienne. Pas Poisson/exponentielle |
| H_1/10 ≈ 1,27·Hs | ✅ CORRECT | Théorie Rayleigh (CEM) |
| H_max ≈ 1,6–2·Hs selon N | ✅ CORRECT | 1,86·Hs (N=1000) à 2,0·Hs (N=3000) ; H_max/Hs ≈ 0,707·√(ln N) |
| "H_moy = 0,626·Hrms" | ⚠️ IMPRÉCIS | H_moy = **0,886·Hrms** ; 0,626 = H_moy/**Hs** |

---

## Marée de vive-eau, backwash & glass-off (ajouts session 12/08 — jour de l'éclipse)

### Vive-eau vs morte-eau (le marnage)
Le **marnage** = amplitude basse mer → pleine mer d'un cycle. Il varie sur ~14,7 j (cycle synodique) :
- **Vive-eau** (grandes marées) autour de la **pleine/nouvelle lune** (Soleil+Lune alignés → marées additives). Marnage max, courants forts. *L'éclipse du 12/08/2026 = nouvelle lune → vive-eau ; marnage hindcast à La Bouverie ~4,7 m.*
- **Morte-eau** (petites marées) aux quadratures (premier/dernier quartier). Marnage min.
- En France on quantifie par le **coefficient de marée** (20 = morte-eau extrême, 120 = vive-eau extrême, 70 = moyen). Open-Meteo donne le niveau de mer `sea_level_height_msl` → on dérive le marnage du jour (max−min) comme proxy du coefficient.

### Backwash (jet de rive descendant)
Après déferlement, l'eau grimpe sur la plage (**swash/jet de rive**) puis **redescend** sous gravité (**backwash**). Quand le backwash est fort, il **percute la vague entrante** → interférence, ressaut, clapot, vagues qui cassent en vrac. Facteurs aggravants :
- **Basse mer de vive-eau** : grande estran découvert + pente de bas de plage + baïnes qui se vident en masse → gros volumes d'eau de retour.
- **Houle courte** (mer du vent) : vagues rapprochées → moins de temps pour que le backwash s'évacue entre deux → collisions plus fréquentes.
- **Baïnes** (plages girondines/charentaises) : chenaux de vidange ; à marée descendante l'eau piégée s'échappe → courant d'arrachement + "plaines d'eau" et vagues parasites. *(Danger = le courant, pas la vague. Vécu 12/08.)*

Implémenté en **science explicative** (`backwash_note`), pas en alerte : déclenché si vive-eau **et** `tide_norm ≤ 0.35`.

### Glass-off du soir (brise thermique)
L'**onshore d'après-midi** en été est souvent une **brise de mer thermique** : la terre chauffe, l'air chaud monte, aspire l'air frais de la mer (vent de mer). Le soir la terre refroidit → la brise **s'effondre** → la mer se lisse (**glass-off**), fréquemment le meilleur créneau. Les modèles grande-maille gardent l'onshore trop tard → **sous-notation systématique du soir** (vérifié sur 4 sessions La Bouverie). Correction heuristique `apply_evening_glassoff` : remonte le facteur vent vers "lisse" de 19h au coucher quand le modèle voit encore de l'onshore.
*Cas extrême du 12/08 : l'éclipse (~99% du soleil masqué) a coupé le chauffage solaire en plein soir → brise tombée avant l'heure → session "kiff" et "bizarre mais mieux". Effet ponctuel non généralisable (on ne calibre pas sur une éclipse).*
