"""
Cœur scientifique de Surfcast.

Tout est explicite et commenté : c'est le module qui transforme les données brutes
(houle, période, direction, vent) en un score ET surtout en une explication du POURQUOI.

Conventions de direction (comme les modèles météo/houle) :
  - "direction" = direction D'OÙ vient la chose (houle ou vent).
  - beach_facing = direction vers laquelle la plage regarde (vers le large).
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field


# --------------------------------------------------------------------------
# 1. PHYSIQUE : énergie et puissance de la houle
# --------------------------------------------------------------------------
# La hauteur seule ne dit RIEN sur la qualité. Ce qui compte c'est l'ÉNERGIE,
# qui dépend du carré de la hauteur ET de la période.
#
#   Énergie par m² :   E = (1/16) * rho * g * Hs²      (rho=1025, g=9.81)
#   Puissance (flux) : P ≈ 0.49 * Hs² * Te   [kW par mètre de crête, eau profonde]
#
# => 0,8 m à 14 s est ~4x plus puissant que 0,8 m à 6 s. C'est LA raison pour
#    laquelle une "petite" houle longue déroule bien et une mer du vent est molle.

def wave_power_kw_m(hs: float, period: float) -> float:
    """Puissance de la houle en kW/m de crête (approximation eau profonde)."""
    if hs is None or period is None:
        return 0.0
    return 0.49 * (hs ** 2) * period


def energy_density_kj_m2(hs: float) -> float:
    """Densité d'énergie en kJ/m² (dépend uniquement de Hs)."""
    rho, g = 1025.0, 9.81
    return (1.0 / 16.0) * rho * g * (hs ** 2) / 1000.0


# --------------------------------------------------------------------------
# 2. NATURE DE LA HOULE : houle longue (groundswell) vs mer du vent (windswell)
# --------------------------------------------------------------------------
# Le seuil de période sépare "propre et organisé" de "clapot mou".

def swell_character(period: float) -> dict:
    """Classe la houle selon sa période de pic."""
    if period is None:
        return {"label": "inconnue", "clean": 0.5, "why": "période inconnue"}
    if period >= 13:
        return {"label": "houle longue puissante", "clean": 1.0,
                "why": f"période {period:.0f}s : houle longue née d'une tempête lointaine, "
                       "très organisée, réfracte bien et casse net"}
    if period >= 11:
        return {"label": "houle longue", "clean": 0.9,
                "why": f"période {period:.0f}s : bonne houle de fond, ça déroule proprement"}
    if period >= 9:
        return {"label": "houle moyenne", "clean": 0.7,
                "why": f"période {period:.0f}s : houle correcte mais moins puissante/organisée"}
    if period >= 7:
        return {"label": "mer du vent courte", "clean": 0.45,
                "why": f"période {period:.0f}s : plutôt mer du vent, vagues rapprochées et peu creuses"}
    return {"label": "clapot / mer du vent", "clean": 0.25,
            "why": f"période {period:.0f}s : mer du vent locale, mou et désorganisé (ce que tu as eu hier)"}


# --------------------------------------------------------------------------
# 3. VENT : offshore (lisse) vs onshore (défonce) — relatif à l'orientation du spot
# --------------------------------------------------------------------------

def _angle_diff(a: float, b: float) -> float:
    """Plus petit écart angulaire absolu entre deux caps (0..180)."""
    d = abs((a - b) % 360.0)
    return min(d, 360.0 - d)


def _geomean(values: list[float]) -> float:
    """Moyenne géométrique = racine n-ième du produit. Contrairement au produit brut,
    elle NE s'effondre PAS quand on combine plein de facteurs "corrects" (cinq 0.85
    donnent 0.85, pas 0.44), tout en gardant "un facteur nul → résultat nul"."""
    vals = [max(0.0, v) for v in values if v is not None]
    if not vals:
        return 1.0
    prod = 1.0
    for v in vals:
        prod *= v
    return prod ** (1.0 / len(vals))


def wind_quality(wind_from: float, wind_speed_kmh: float, offshore_dir: float) -> dict:
    """
    Qualité liée au vent, entre 0.3 (défoncé) et 1.0 (glassy/offshore).
    wind_from    : direction d'où vient le vent
    offshore_dir : direction d'où vient le vent offshore idéal (vent de terre)
    """
    if wind_from is None or wind_speed_kmh is None:
        return {"factor": 0.8, "label": "vent inconnu", "why": "données de vent absentes"}

    diff = _angle_diff(wind_from, offshore_dir)          # 0 = plein offshore, 180 = plein onshore
    alignment = math.cos(math.radians(diff))             # +1 offshore ... -1 onshore

    if wind_speed_kmh <= 6:
        return {"factor": 0.97, "label": "quasi glassy",
                "why": f"vent faible ({wind_speed_kmh:.0f} km/h) : surface lisse, peu importe la direction"}

    # 0 (onshore) .. 1 (offshore)
    orient = 0.5 * (alignment + 1.0)
    # Le vent fort amplifie l'effet (bon si offshore, catastrophique si onshore)
    speed_amp = min(1.0, wind_speed_kmh / 30.0)
    factor = 0.65 + 0.35 * alignment - 0.25 * speed_amp * (1 - orient)
    factor = max(0.3, min(1.0, factor))

    if diff <= 45:
        label, txt = "offshore", "vent de terre : il tient la vague ouverte et la lisse"
    elif diff <= 80:
        label, txt = "offshore de biais", "vent de terre légèrement de côté, conditions plutôt propres"
    elif diff <= 100:
        label, txt = "cross-shore", "vent de travers : surface un peu hachée"
    elif diff <= 135:
        label, txt = "onshore de biais", "vent de mer de biais : ça commence à défoncer"
    else:
        label, txt = "onshore", "vent de mer de face : mer clapoteuse, vagues molles et fermées"

    return {"factor": factor, "label": label,
            "why": f"{txt} ({wind_speed_kmh:.0f} km/h)"}


# --------------------------------------------------------------------------
# 4. DIRECTION DE HOULE : est-ce que la houle rentre vraiment dans le spot ?
# --------------------------------------------------------------------------

def swell_direction_quality(swell_from: float, window: list[float]) -> dict:
    """Est-ce que la houle vient d'une direction qui atteint le spot ?
    Le label est DÉRIVÉ du facteur → la couleur (via le facteur) colle toujours au label."""
    if swell_from is None:
        return {"factor": 0.8, "label": "direction inconnue", "why": "direction de houle absente"}
    lo, hi = window
    center = (lo + hi) / 2.0
    half = (hi - lo) / 2.0
    off = _angle_diff(swell_from, center)
    if off <= half:
        factor = round(0.85 + 0.15 * (1 - off / half), 2)   # 0.85..1.0 → vert
    else:
        over = off - half
        factor = round(max(0.15, 0.75 - over / 50.0), 2)    # décroît hors fenêtre

    if factor >= 0.7:
        label = "bien orientée"
        why = f"houle de {swell_from:.0f}° : pile dans la fenêtre du spot"
    elif factor >= 0.45:
        label = "un peu de biais"
        why = f"houle de {swell_from:.0f}° : rentre de biais, une partie de l'énergie passe à côté"
    else:
        label = "mal orientée"
        why = f"houle de {swell_from:.0f}° : hors fenêtre, le spot est en partie masqué"
    return {"factor": factor, "label": label, "why": why}


# --------------------------------------------------------------------------
# 4b. TAILLE DE VAGUE (déferlante) et adjectifs — distincte de la taille de HOULE
# --------------------------------------------------------------------------

def breaking_height(hs: float, period: float) -> float:
    """Hauteur de la vague qui DÉFERLE (au bord), via l'indice de Komar-Gaughan.
    C'est la 'taille de vague' réelle, différente de la hauteur de houle au large."""
    if not hs or not period:
        return 0.0
    L0 = 1.56 * period * period
    return hs * 0.56 * (hs / L0) ** (-0.2)


def shelter_factor(period: float, spot: dict) -> float:
    """Fraction de la houle du LARGE qui atteint réellement le spot (1.0 = plein exposé).

    Pourquoi c'est nécessaire : Open-Meteo donne le Hs d'une maille de ~5-10 km, donc
    la houle AU LARGE. Pour un beach break exposé c'est une bonne approximation. Pour un
    spot au fond d'une anse, c'est faux : la houle doit contourner une pointe pour entrer,
    et elle y perd l'essentiel de son énergie. Sans correction, un spot abrité afficherait
    la même taille que la plage exposée d'à côté, et paraîtrait surfable les jours où il
    est plat.

    La correction dépend de la PÉRIODE, et c'est là qu'est la physique : une houle longue
    diffracte et réfracte bien mieux qu'un clapot court. C'est exactement ce que décrivent
    les guides de L'Embarcadère — il faut 13-14 s pour que ça rentre dans la baie, une mer
    du vent de 7 s n'y arrive jamais, quelle que soit sa hauteur au large.

    Spot sans les clés shelter_* → 1.0, comportement inchangé (tous les spots existants).
    """
    lo = spot.get("shelter_short")
    hi = spot.get("shelter_long")
    if lo is None and hi is None:
        return 1.0
    lo = 1.0 if lo is None else float(lo)
    hi = 1.0 if hi is None else float(hi)
    t_lo = float(spot.get("shelter_t_short", 6.0))
    t_hi = float(spot.get("shelter_t_long", 14.0))
    if period is None or t_hi <= t_lo:
        return (lo + hi) / 2.0
    x = max(0.0, min(1.0, (period - t_lo) / (t_hi - t_lo)))
    return lo + (hi - lo) * x


def wave_size_label(hb: float) -> dict:
    """Adjectif de taille + facteur 0..1 pour la barre (petit = barre basse = rouge)."""
    if hb < 0.4:
        return {"label": "quasi plates", "factor": 0.12}
    if hb < 0.7:
        return {"label": "petites", "factor": 0.32}
    if hb < 1.1:
        return {"label": "correctes", "factor": 0.55}
    if hb < 1.7:
        return {"label": "bonnes", "factor": 0.8}
    if hb < 2.6:
        return {"label": "grosses", "factor": 0.95}
    return {"label": "très grosses", "factor": 1.0}


def power_label(power: float) -> str:
    """Adjectif d'ÉNERGIE (pas de taille) pour la carte énergie / l'horaire."""
    if power < 1:
        return "très faible"
    if power < 5:
        return "faible"
    if power < 15:
        return "correcte"
    if power < 35:
        return "bonne"
    if power < 70:
        return "forte"
    return "énorme"


# --------------------------------------------------------------------------
# 4c. NIVEAU DU SURFEUR : la taille idéale N'EST PAS "le plus gros possible".
# --------------------------------------------------------------------------
# Pour un débutant, 0,5 m propre = nickel, et 2 m = trop/dangereux. La taille
# se note en CLOCHE autour d'une zone idéale, pas en échelle monotone d'énergie.
#   min : en-dessous = quasi rien à surfer
#   lo..hi : zone idéale (note pleine)
#   max : au-dessus = trop gros pour ce niveau
#   clean_floor : à quel point la "propreté" (période/vent) compte peu (débutant = peu)

# Taille = hauteur déferlante estimée à partir de la mer TOTALE (Hs). Fenêtres calées
# sur le ressenti surfeur (un débutant se régale de 0,6-1,3 m, 2 m+ = trop).
# clean_floor élevé = la propreté (période) compte peu pour un débutant (il surfe très
# bien du petit clapot mou).
# wind_floor : plancher du facteur vent selon le niveau. Un débutant surfe la mousse /
# les reforms près du bord → l'onshore le gêne BEAUCOUP moins qu'un confirmé sur une
# face verte. Vérifié : sessions onshore appréciées (15/08 15-16h, 12/08) mais
# que le modèle sous-notait. Un confirmé, lui, veut du propre → plancher bas.
LEVELS = {
    "debutant":      {"min": 0.3, "lo": 0.7, "hi": 1.3, "max": 2.0, "clean_floor": 0.78, "wind_floor": 0.55, "label": "débutant"},
    "intermediaire": {"min": 0.5, "lo": 1.0, "hi": 2.0, "max": 3.2, "clean_floor": 0.55, "wind_floor": 0.4, "label": "intermédiaire"},
    "confirme":      {"min": 0.7, "lo": 1.3, "hi": 3.5, "max": 6.0, "clean_floor": 0.3, "wind_floor": 0.25, "label": "confirmé"},
}


def size_fit(hb: float, lv: dict) -> float:
    """0..1 : adéquation de la taille au niveau. MONTE à travers la zone idéale
    (plus gros = mieux jusqu'au pic), puis redescend quand ça devient trop gros."""
    mn, lo, hi, mx = lv["min"], lv["lo"], lv["hi"], lv["max"]
    if hb <= 0:
        return 0.0
    if hb < mn:
        return max(0.0, hb / mn) * 0.35             # sous le minimum ridable
    if hb < lo:
        return 0.35 + 0.35 * (hb - mn) / (lo - mn)  # 0.35 → 0.70 (petit mais surfable)
    if hb <= hi:
        return 0.70 + 0.30 * (hb - lo) / (hi - lo)  # 0.70 → 1.00 : plus gros = mieux
    if hb <= mx:
        return 1.0 - 0.45 * (hb - hi) / (mx - hi)    # ça devient trop gros
    return max(0.25, 0.55 - 0.1 * (hb - mx))        # bien trop gros pour le niveau


# --------------------------------------------------------------------------
# 4d. MARÉE & TYPE DE DÉFERLANTE (plongeante / glissante / gonflante)
# --------------------------------------------------------------------------
# La houle ne change pas d'une heure à l'autre, mais la MARÉE change la
# profondeur — donc où et COMMENT la vague déferle. À pleine mer elle casse
# sur la marche de plage raide → déferlante plongeante qui "claque" (shorebreak).
# À basse/mi-marée elle casse plus au large sur un banc plus plat → glissante.
#
# Type de déferlante = nombre d'Iribarren  ξ = pente / √(H/L0),  L0 = 1.56·T².
#   ξ < 0.4  : glissante (spilling)   — mousse qui glisse, douce
#   0.4–2.0  : plongeante (plunging)  — lèvre projetée, ça creuse et ça claque
#   ξ > 2.0  : gonflante (surging)    — se soulève et dumpe d'un coup près du bord
# La marée module la PENTE effective : pleine mer = marche raide, basse = banc plat.
# (Validé par les sessions du 27/07 à La Bouverie : pleine mer 16h = shorebreak
#  violent, marée descendante 20h = mer propre.)

def _deep_wavelength(period: float) -> float:
    return 1.56 * period * period


def iribarren(hb: float, period: float, slope: float) -> float:
    L0 = _deep_wavelength(period)
    if hb <= 0 or L0 <= 0:
        return 0.0
    return slope / math.sqrt(hb / L0)


def breaker_from_xi(xi: float) -> tuple[str, str]:
    if xi < 0.4:
        return "glissante", "la mousse glisse doucement sur la face, ça déroule (spilling)"
    if xi < 2.0:
        return "plongeante", "la lèvre est projetée en avant, ça creuse et ça claque (plunging)"
    return "gonflante", "la vague se soulève et dumpe d'un coup près du bord (surging)"


def tide_state_label(tide_norm: float, tide_trend: float) -> str:
    if tide_norm is None:
        return "marée inconnue"
    where = "pleine mer" if tide_norm >= 0.82 else "basse mer" if tide_norm <= 0.18 else "mi-marée"
    if tide_trend is None or abs(tide_trend) < 0.05 or where in ("pleine mer", "basse mer"):
        return where
    return where + (" montante" if tide_trend > 0 else " descendante")


def tide_breaker_quality(hb, period, tide_norm, tide_trend, spot, level="debutant") -> dict:
    """Effet de la marée : type de déferlante + facteur qualité + alerte shorebreak."""
    if tide_norm is None or not hb or not period:
        return {"factor": 1.0, "label": "marée n.d.", "breaker": None,
                "state": "marée inconnue", "why": "pas de donnée de marée",
                "shorebreak": False, "norm": None}

    slope_low = spot.get("slope_low", 0.02)     # banc plat de basse mer → spilling
    slope_high = spot.get("slope_high", 0.09)   # marche de plage raide → plunging/shorebreak
    slope_eff = slope_low + (slope_high - slope_low) * max(0.0, min(1.0, tide_norm))
    xi = iribarren(hb, period, slope_eff)
    btype, _bwhy = breaker_from_xi(xi)
    state = tide_state_label(tide_norm, tide_trend)

    # shorebreak qui dumpe : marée haute (plein d'eau → la vague casse sur la marche de
    # plage raide) + houle COURTE (mer du vent) + pente effective raide. Une houle LONGUE
    # à marée haute donne un beau tube, pas un shorebreak → on exige period < 9 s.
    dumping = tide_norm >= 0.75 and (period or 99) < 9.0 and slope_eff >= 0.06

    if dumping:
        factor, label = 0.4, "shorebreak (dumpe)"
        why = f"{state} : la vague casse sur la marche de plage → shorebreak qui dumpe et qui claque"
    elif btype == "glissante":
        factor, label = 0.9, "glissante (douce)"
        why = f"{state} : déferlante glissante, douce — idéale pour progresser"
    elif btype == "plongeante":
        factor = 0.9 if level == "confirme" else 0.8
        label = "plongeante (rouleaux)"
        why = f"{state} : déferlante plongeante, beaux rouleaux mais plus engagés"
    else:  # gonflante hors shorebreak
        factor, label = 0.6, "gonflante"
        why = f"{state} : déferlante gonflante, casse mollement près du bord"

    # bonus si dans la fenêtre de marée idéale du spot (normalisée 0=basse..1=pleine)
    ideal = spot.get("tide_ideal")
    if ideal and ideal[0] <= tide_norm <= ideal[1]:
        factor = min(1.0, factor + 0.1)

    return {"factor": round(factor, 2), "label": label, "breaker": btype,
            "state": state, "why": why, "shorebreak": dumping,
            "xi": round(xi, 2), "norm": tide_norm}


def annotate_tide(conds: list) -> None:
    """Remplit tide_norm (0=basse mer .. 1=pleine mer) et tide_trend (m/h) à partir de
    tide_m, sur l'ensemble fourni (une journée ou un forecast). Modifie en place."""
    vals = [c.tide_m for c in conds if c.tide_m is not None]
    if len(vals) < 3:
        return
    lo, hi = min(vals), max(vals)
    rng = hi - lo
    for i, c in enumerate(conds):
        if c.tide_m is None:
            continue
        c.tide_norm = round((c.tide_m - lo) / rng, 3) if rng > 0.05 else 0.5
        c.tide_range = round(rng, 2)   # marnage : gros = vive-eau (grandes marées)
        prev = conds[i - 1].tide_m if i > 0 else None
        nxt = conds[i + 1].tide_m if i < len(conds) - 1 else None
        if prev is not None and nxt is not None:
            c.tide_trend = round((nxt - prev) / 2.0, 3)
        elif nxt is not None:
            c.tide_trend = round(nxt - c.tide_m, 3)
        elif prev is not None:
            c.tide_trend = round(c.tide_m - prev, 3)


# --------------------------------------------------------------------------
# 4e. GLASS-OFF DU SOIR : la brise de mer thermique tombe au coucher
# --------------------------------------------------------------------------
# En été, l'onshore d'après-midi est une BRISE THERMIQUE (la terre chauffe, aspire
# l'air de la mer). Le soir la terre refroidit → la brise s'effondre → la mer se
# lisse ("glass-off"), souvent le meilleur créneau. Les modèles grande-maille
# (Open-Meteo) gardent souvent cet onshore trop longtemps → score du soir trop bas.
# Vérifié sur 4 sessions à La Bouverie (27/07 soir, 12/08 kiff+soir d'éclipse) :
# le modèle sous-notait systématiquement les créneaux offshore/soir.
#
# Correction : quand le vent modèle est onshore-ish ET qu'on approche du coucher,
# on remonte le facteur vent vers "lisse". C'est une HEURISTIQUE locale assumée,
# désactivable par spot (evening_glassoff: false).

def apply_evening_glassoff(wind_factor: float, hour: int, spot: dict) -> tuple[float, bool]:
    """Remonte le facteur vent le soir si le modèle voit encore de l'onshore.
    Retourne (facteur_corrigé, appliqué?)."""
    if not spot.get("evening_glassoff", True):
        return wind_factor, False
    if wind_factor >= 0.72 or hour < 19:     # déjà propre, ou pas encore le soir
        return wind_factor, False
    ramp = min(1.0, (hour - 19) / 2.5)        # 0 à 19h → 1 vers 21h30
    if ramp <= 0.05:
        return wind_factor, False
    target = 0.85                             # vers "quasi lisse" au coucher
    corrected = wind_factor + ramp * (target - wind_factor)
    return round(corrected, 2), True


# --------------------------------------------------------------------------
# 4f. VIVE-EAU / MORTE-EAU et BACKWASH (science explicative, pas une alerte)
# --------------------------------------------------------------------------
# Le MARNAGE (amplitude basse→pleine mer du jour) dit si on est en vive-eau
# (grandes marées, pleine/nouvelle lune) ou morte-eau. En vive-eau, la plage se
# découvre beaucoup à marée basse : l'eau qui a grimpé sur le sable redescend en
# masse (+ les baïnes se vident) → BACKWASH = eau de retour qui percute les vagues
# entrantes → clapot, "plaines d'eau", vagues qui cassent en vrac. Effet maximal à
# basse mer de vive-eau avec une houle courte (mer du vent).

def tide_amplitude_label(tide_range: float, spot: dict) -> dict:
    """Classe le marnage du jour : vive-eau / moyenne / morte-eau."""
    if tide_range is None:
        return {"label": None, "range": None}
    vive = spot.get("range_vive", 4.2)    # seuils Atlantique (Gironde/Charente) par défaut
    morte = spot.get("range_morte", 2.5)
    if tide_range >= vive:
        lab = "vive-eau (grandes marées)"
    elif tide_range <= morte:
        lab = "morte-eau (petites marées)"
    else:
        lab = "marée moyenne"
    return {"label": lab, "range": round(tide_range, 1),
            "vive": tide_range >= vive}


def backwash_note(tide_norm, tide_range, period, spot) -> str | None:
    """Phrase explicative sur le backwash quand les conditions s'y prêtent (basse
    mer de vive-eau). Renvoie None si non pertinent. PAS une alerte de sécurité."""
    if tide_norm is None or tide_range is None:
        return None
    amp = tide_amplitude_label(tide_range, spot)
    if amp["vive"] and tide_norm <= 0.35:
        extra = " (houle courte → l'effet est plus marqué)" if (period or 99) < 9 else ""
        return (f"Marée basse de {amp['label']} (marnage ~{amp['range']} m) : la plage se "
                f"découvre, l'eau de retour et les baïnes qui se vident créent du backwash "
                f"qui parasite certaines vagues{extra}. Vise les vagues bien parallèles "
                f"entre les veines de courant.")
    return None


# --------------------------------------------------------------------------
# 4g. ORGANISATION DE LA MER : "bien rangée" vs "chantier" (étalement directionnel)
# --------------------------------------------------------------------------
# Les pros lisent l'ÉTALEMENT DIRECTIONNEL du spectre : une houle concentrée (un seul
# train, une direction) fait des lignes propres ; plusieurs trains de directions
# différentes + de la mer du vent = surface en désordre (pics croisés, vagues qui
# ferment). Open-Meteo ne fournit pas l'étalement, mais on peut l'approcher avec ce
# qu'on a : la part d'ÉNERGIE de la mer du vent dans la mer totale (énergie ∝ H², donc
# on compare des H²), et l'écart de direction entre les deux trains de houle.
# Indicateur INFORMATIF, hors score, tant qu'il n'est pas calibré sur des sessions.

def sea_organisation(c) -> dict:
    hs = c.swell_h or 0.0
    if hs < 0.1:
        return {"label": None, "factor": None, "why": "pas assez de mer pour juger"}
    ww = c.wind_wave_h or 0.0
    windsea = min(1.0, (ww * ww) / (hs * hs))          # part d'énergie de la mer du vent
    cross = None
    if (c.sw1_h and c.sw2_h and c.sw2_h >= 0.2 and c.sw1_dir is not None
            and c.sw2_dir is not None and c.sw2_h >= 0.4 * c.sw1_h):
        cross = _angle_diff(c.sw1_dir, c.sw2_dir)      # 2 trains comparables, croisés ?
    factor = 1.0 - 0.7 * windsea
    if cross is not None and cross > 30:
        factor -= min(0.3, (cross - 30) / 200.0)       # 30° → 0, 90° → -0.3
    factor = round(max(0.1, factor), 2)

    bits = []
    if windsea >= 0.15:
        bits.append(f"mer du vent = {windsea * 100:.0f} % de l'énergie")
    if cross is not None and cross > 30:
        bits.append(f"2 trains de houle croisés à {cross:.0f}°")
    if factor >= 0.75:
        label = "mer bien rangée"
        why = "une houle dominante, une direction : lignes propres" + (f" ({'; '.join(bits)})" if bits else "")
    elif factor >= 0.5:
        label = "mer un peu mélangée"
        why = "; ".join(bits) or "houle et mer du vent se partagent l'énergie"
    else:
        label = "chantier (mer croisée)"
        why = ("; ".join(bits) or "beaucoup de mer du vent") + " → pics qui se croisent, vagues qui ferment"
    return {"label": label, "factor": factor, "why": why,
            "windsea_share": round(windsea, 2), "cross_deg": round(cross) if cross is not None else None}


# --------------------------------------------------------------------------
# 5. SCORE ÉNERGIE : de la puissance (kW/m) vers une note 0..10
# --------------------------------------------------------------------------

_ENERGY_STEPS = [
    (0.0, 0.0, "plat"),
    (1.5, 1.5, "quasi plat"),
    (5.0, 3.0, "petit"),
    (12.0, 5.0, "fun, surfable"),
    (30.0, 7.0, "bon, consistant"),
    (60.0, 8.5, "solide et puissant"),
    (120.0, 10.0, "gros / costaud"),
]


def energy_score(power_kw_m: float) -> dict:
    """Convertit la puissance en note 0..10 avec interpolation linéaire par paliers."""
    steps = _ENERGY_STEPS
    if power_kw_m <= steps[0][0]:
        return {"score": 0.0, "label": steps[0][2]}
    for (p0, s0, _l0), (p1, s1, l1) in zip(steps, steps[1:]):
        if power_kw_m <= p1:
            frac = (power_kw_m - p0) / (p1 - p0)
            return {"score": round(s0 + frac * (s1 - s0), 1), "label": l1}
    return {"score": 10.0, "label": steps[-1][2]}


# --------------------------------------------------------------------------
# 6. ÉVALUATION COMPLÈTE D'UN CRÉNEAU HORAIRE
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# 4c. THERMIQUE : quelle combinaison, et est-ce que je vais cailler ?
# --------------------------------------------------------------------------
# N'ENTRE PAS dans le score : une eau à 12 °C ne rend pas les vagues moins bonnes,
# elle rend la session moins agréable. C'est un indicateur de CONFORT, séparé.
#
# Fenêtres de confort en °C d'eau RESSENTIE (voir plus bas), pour une session
# d'environ 1 h 30. Ce sont les plages usuelles des fabricants, resserrées sur
# l'Atlantique français (eau agitée = on se refroidit plus vite qu'en piscine).

WETSUITS = {
    "boardshort": (24.0, 99.0, "boardshort"),
    "shorty":     (21.0, 24.5, "shorty / top néoprène"),
    "3/2":        (16.5, 22.0, "combinaison 3/2"),
    "4/3":        (12.5, 18.0, "combinaison 4/3"),
    "5/4":        (8.0, 14.0, "combinaison 5/4"),
}
# Les fenêtres se CHEVAUCHENT volontairement : entre 16,5 et 18 °C une 3/2 et une 4/3
# conviennent toutes les deux, c'est une affaire de frilosité et de durée de session.
DEFAULT_SUIT = "3/2"


def felt_water_temp(water: float, air: float, wind_kmh: float) -> float:
    """Température d'eau « ressentie » sur une session.

    On ne surfe pas immergé en permanence : on passe le plus clair du temps ASSIS
    sur la planche, torse et tête à l'air. Quand l'air est plus froid que l'eau et
    qu'il vente, le corps se refroidit BEAUCOUP plus vite que ce que la seule
    température de l'eau laisse croire — c'est l'évaporation sur le néoprène mouillé.

    On applique donc une pénalité, plafonnée à 3 °C pour qu'elle ne domine jamais la
    mesure réelle de l'eau. Air plus chaud que l'eau → aucune pénalité (cas de l'été).
    """
    if water is None:
        return None
    if air is None or wind_kmh is None or air >= water:
        return water
    ecart = water - air
    vent = min(1.0, wind_kmh / 30.0)          # 30 km/h = effet plein
    penalite = min(3.0, 0.25 * ecart * (0.4 + 0.6 * vent))
    return round(water - penalite, 1)


def wetsuit_advice(water: float, air: float, wind_kmh: float, suit: str = DEFAULT_SUIT) -> dict:
    """Confort thermique pour LA combinaison de l'utilisateur + ce qu'il faudrait idéalement."""
    if water is None:
        return {"water": None, "why": "température de l'eau non disponible"}

    felt = felt_water_temp(water, air, wind_kmh)
    lo, hi, nom = WETSUITS.get(suit, WETSUITS[DEFAULT_SUIT])

    # Combinaison idéale = celle dont la fenêtre contient le ressenti (la plus chaude
    # qui convient, en partant des plus légères).
    ideal = None
    for k in ("boardshort", "shorty", "3/2", "4/3", "5/4"):
        klo, khi, knom = WETSUITS[k]
        if klo <= felt <= khi:
            ideal = k
            break
    if ideal is None:
        ideal = "5/4" if felt < 8.0 else "boardshort"

    # Accessoires : ce sont les extrémités qui lâchent en premier.
    accessoires = []
    if felt < 15.0:
        accessoires.append("chaussons")
    if felt < 13.0:
        accessoires.append("gants")
    if felt < 11.0:
        accessoires.append("cagoule")

    if felt > hi:
        verdict, ok = "trop chaud", True
        why = (f"eau à {water:.1f} °C : ta {nom} sera trop chaude. "
               "Pas gênant — laisse entrer un peu d'eau au col pour te rafraîchir, "
               f"ou passe en {WETSUITS[ideal][2]}.")
    elif felt >= lo + 1.5:
        verdict, ok = "idéal", True
        why = f"eau à {water:.1f} °C : ta {nom} est pile dans sa fenêtre, session confortable."
    elif felt >= lo:
        verdict, ok = "limite basse", True
        why = (f"eau ressentie {felt:.1f} °C : ta {nom} passe encore, mais tu es en bas de "
               "sa plage — prévois une session plus courte"
               + (f", et des {' + '.join(accessoires)}" if accessoires else "") + ".")
    else:
        verdict, ok = "trop froid", False
        manque = lo - felt
        why = (f"eau ressentie {felt:.1f} °C, soit {manque:.1f} °C sous la limite de ta {nom} "
               f"({lo:.0f} °C) : tu vas cailler. Il faudrait une {WETSUITS[ideal][2]}"
               + (f" + {' + '.join(accessoires)}" if accessoires else "") + ".")

    # Le vent mérite d'être signalé quand c'est LUI qui fait basculer le confort.
    note_vent = None
    if felt is not None and water - felt >= 1.0:
        note_vent = (f"L'eau est à {water:.1f} °C mais l'air à {air:.0f} °C avec "
                     f"{wind_kmh:.0f} km/h de vent : entre deux séries tu ressentiras "
                     f"plutôt {felt:.1f} °C.")

    return {"water": round(water, 1), "air": round(air, 1) if air is not None else None,
            "felt": felt, "suit": suit, "suit_label": nom, "verdict": verdict, "ok": ok,
            "ideal": ideal, "ideal_label": WETSUITS[ideal][2],
            "accessoires": accessoires, "why": why, "note_vent": note_vent,
            "limite_basse": lo, "limite_haute": hi}


@dataclass
class Conditions:
    """Données brutes d'un créneau (une heure)."""
    time: str
    swell_h: float          # hauteur houle (m)
    swell_period: float     # période de pic de la houle (s)
    swell_dir: float        # direction d'où vient la houle (deg)
    wind_wave_h: float      # hauteur mer du vent (m)
    wind_speed: float       # vitesse vent (km/h)
    wind_dir: float         # direction d'où vient le vent (deg)
    tide_m: float = None       # marée : niveau de mer rel. niveau moyen (m)
    tide_norm: float = None    # 0 = basse mer, 1 = pleine mer (rempli par annotate_tide)
    tide_trend: float = None   # variation (m/h) : + montante, - descendante
    tide_range: float = None   # marnage du jour (m) = amplitude basse→pleine (vive-eau vs morte-eau)
    # Trains de houle séparés (le TOTAL reste dans swell_h/period/dir, gardé pour la taille).
    # sw1 = houle primaire, sw2 = houle secondaire (ex : houle de fond longue sous le clapot).
    sw1_h: float = None
    sw1_t: float = None
    sw1_dir: float = None
    sw2_h: float = None
    sw2_t: float = None
    sw2_dir: float = None
    # Thermique : sert UNIQUEMENT au conseil de combinaison, jamais au score.
    water_temp: float = None   # température de l'eau (°C)
    air_temp: float = None     # température de l'air à 2 m (°C)
    feels_like: float = None   # ressenti air (°C, inclut déjà le vent côté Open-Meteo)


@dataclass
class Evaluation:
    time: str
    score: float
    label: str
    power_kw_m: float
    wave_h: float = 0.0                            # taille de vague déferlante (m)
    headline: str = ""                             # punchline courte
    drivers: dict = field(default_factory=dict)   # décomposition pour l'UI
    explanation: str = ""                          # texte long (replié)


def dominant_swell(c: Conditions):
    """Parmi les trains de houle (primaire sw1, secondaire sw2), retourne celui qui fait
    les MEILLEURES vagues = celui qui DÉFERLE le plus gros, + le 2e train s'il existe.
    Comme une houle longue shoale davantage, ce critère met en avant la houle de fond
    même quand la mer du vent domine la hauteur totale. Retourne (dominant, autre) ou (None, None)."""
    comps = [(h, t, dr) for (h, t, dr) in
             [(c.sw1_h, c.sw1_t, c.sw1_dir), (c.sw2_h, c.sw2_t, c.sw2_dir)]
             if h and t and h >= 0.05]
    if not comps:
        return None, None
    comps.sort(key=lambda x: breaking_height(x[0], x[1]), reverse=True)
    return comps[0], (comps[1] if len(comps) > 1 else None)


def groundswell_note(dom, sw2) -> str | None:
    """Signale une houle de fond LONGUE et significative (le train propre sous le clapot)."""
    for comp in (dom, sw2):
        if comp and comp[1] and comp[0] and comp[1] >= 10 and comp[0] >= 0.15:
            return (f"🌊 Houle de fond de {comp[0]:.1f} m à {comp[1]:.0f} s (longue période) : "
                    f"c'est elle qui fait les belles séries propres sous le clapot.")
    return None


def evaluate(c: Conditions, spot: dict, level: str = "debutant") -> Evaluation:
    """Score de SURFABILITÉ pour un niveau donné (pas un score d'énergie brute)."""
    lv = LEVELS.get(level, LEVELS["debutant"])
    # Houles : la TAILLE vient de la mer totale (comme les sites de report), mais la
    # PROPRETÉ et l'ORIENTATION viennent du train qui casse le mieux (souvent la houle de
    # fond, longtemps ignorée quand la mer du vent domine la période moyenne).
    dom, sw2 = dominant_swell(c)
    surf_t = dom[1] if dom else c.swell_period
    surf_dir = dom[2] if (dom and dom[2] is not None) else c.swell_dir
    # Abri : fraction de la houle du large qui entre réellement (1.0 pour un spot exposé).
    # Appliqué AVANT le calcul de taille et de puissance, sinon un spot d'anse hériterait
    # de la houle de la plage exposée voisine (même maille du modèle).
    shelter = shelter_factor(surf_t, spot)
    hs_eff = c.swell_h * shelter
    power = wave_power_kw_m(hs_eff, c.swell_period)
    char = swell_character(surf_t)
    wind = wind_quality(c.wind_dir, c.wind_speed, spot["offshore_dir"])
    sdir = swell_direction_quality(surf_dir, spot["swell_window"])
    hb = breaking_height(hs_eff, c.swell_period)
    size = wave_size_label(hb)

    # Plancher vent selon le niveau : l'onshore gêne moins un débutant (mousse/reforms)
    # qu'un confirmé (face verte). Remonte le facteur vent vers le plancher du niveau.
    wf = lv["wind_floor"]
    if wind["factor"] < 1.0:
        wind = {**wind, "factor": round(wf + (1 - wf) * wind["factor"], 2)}

    # Glass-off du soir : la brise thermique onshore tombe au coucher (le modèle la
    # garde trop longtemps). On travaille sur un vent EFFECTIF corrigé.
    hour = int(c.time[11:13]) if c.time and len(c.time) >= 13 else 12
    wind_eff_f, glassoff = apply_evening_glassoff(wind["factor"], hour, spot)
    if glassoff:
        wind = {**wind, "factor": wind_eff_f, "label": wind["label"] + " → glass-off",
                "why": wind["why"] + " — mais la brise du soir tombe (glass-off), ça se lisse au coucher"}

    # Taille en cloche selon le niveau ; propreté adoucie pour les débutants.
    # Orientation = modificateur DOUX (floor 0.6) : une petite houle mal orientée ne doit
    # pas écraser un spot où il y a de la taille (la mer du vent rentre quand même).
    sfit = size_fit(hb, lv)
    tide = tide_breaker_quality(hb, c.swell_period, c.tide_norm, c.tide_trend, spot, level)
    amp = tide_amplitude_label(c.tide_range, spot)
    clean_eff = lv["clean_floor"] + (1 - lv["clean_floor"]) * char["clean"]
    orient_eff = 0.6 + 0.4 * sdir["factor"]
    # Agrégation des facteurs QUALITÉ en moyenne GÉOMÉTRIQUE (au lieu d'un produit qui
    # s'effondre : cinq 0.85 donnaient 0.44 → biais "-3" permanent). La taille (sfit) reste
    # un GATE dur (plat = pas de surf), et le SHOREBREAK reste un plafond dur (rend injouable
    # même si tout le reste est bon) → la geomean ne "dilue" pas les jours injouables.
    if tide["shorebreak"]:
        quality = _geomean([clean_eff, wind["factor"], orient_eff])
        raw = 10.0 * sfit * quality * tide["factor"]     # shorebreak = plafond dur
    else:
        quality = _geomean([clean_eff, wind["factor"], orient_eff, tide["factor"]])
        raw = 10.0 * sfit * quality
    score = round(min(10.0, raw), 1)
    too_big = hb > lv["max"]
    label = _surf_label(score, hb, lv, too_big)

    drivers = {
        # la barre "Vagues" reflète l'ADÉQUATION à ton niveau (vert = idéale pour toi)
        "vague": {"h": round(hb, 2), "label": size["label"], "factor": round(sfit, 2)},
        # h = houle AU LARGE (ce que donnent les sites de report) ; h_spot = ce qui entre
        # vraiment quand le spot est abrité. Egaux si shelter == 1.
        "houle": {"h": c.swell_h, "h_spot": round(hs_eff, 2) if shelter < 1.0 else None,
                  "abri": round(shelter, 2) if shelter < 1.0 else None,
                  "periode": c.swell_period, "dir": c.swell_dir,
                  "label": char["label"], "clean": char["clean"],
                  "surf_periode": round(surf_t, 1) if surf_t else None,
                  "secondaire": ({"h": round(sw2[0], 2), "periode": round(sw2[1], 1),
                                  "dir": round(sw2[2]) if sw2[2] is not None else None}
                                 if sw2 else None)},
        "vent": {"speed": c.wind_speed, "dir": c.wind_dir, "glassoff": glassoff, **wind},
        "orientation": sdir,
        "maree": {"state": tide["state"], "norm": tide.get("norm"), "breaker": tide["breaker"],
                  "label": tide["label"], "factor": tide["factor"], "why": tide["why"],
                  "shorebreak": tide["shorebreak"], "amplitude": amp["label"],
                  # niveau horaire (m rel. niveau moyen) + marnage → courbe de marée côté UI
                  "level": c.tide_m, "range": c.tide_range},
        # Puissance = flux d'énergie (kW/m, ∝ H²·T) ; density = énergie par m² (kJ/m², ∝ H²).
        # Les deux sont affichées car les sites de report disent "énergie" pour l'une ou l'autre.
        "energie": {"value": round(power, 1), "unit": "kW/m", "label": power_label(power),
                    "density_kj_m2": round(energy_density_kj_m2(hs_eff), 1)},
        # Organisation de la mer (proxy d'étalement directionnel) : informatif, hors score.
        "mer": sea_organisation(c),
        # Confort thermique : informatif, VOLONTAIREMENT hors du calcul du score.
        "thermique": wetsuit_advice(c.water_temp, c.air_temp, c.wind_speed, spot.get("suit", DEFAULT_SUIT)),
    }

    headline = build_headline(score, hb, lv, char, wind, sdir, too_big, tide)
    explanation = build_explanation(score, label, c, char, wind, sdir, power, spot, tide)
    gn = groundswell_note(dom, sw2)
    if gn:
        explanation += " " + gn
    bw = backwash_note(c.tide_norm, c.tide_range, c.swell_period, spot)
    if bw:
        explanation += " " + bw

    return Evaluation(time=c.time, score=score, label=label, power_kw_m=round(power, 1),
                      wave_h=round(hb, 2), headline=headline, drivers=drivers,
                      explanation=explanation)


def _surf_label(score, hb, lv, too_big) -> str:
    if too_big:
        return "trop gros pour toi"
    if hb < lv["min"] * 0.8:
        return "plat, rien à surfer"
    if score < 2:
        return "faible"
    if score < 4:
        return "petit mais surfable"
    if score < 6:
        return "sympa"
    if score < 8:
        return "bien !"
    return "excellent"


def build_headline(score, hb, lv, char, wind, sdir, too_big, tide=None) -> str:
    """Punchline courte et HONNÊTE : positive quand c'est surfable, sinon les points faibles."""
    if too_big:
        return f"vagues ~{hb:.1f} m, trop gros pour ton niveau"
    if hb < lv["min"] * 0.8:
        return "quasiment plat, rien à ramer"
    if tide and tide.get("shorebreak"):
        return f"⚠️ shorebreak qui dumpe à {tide['state']} — dur de sortir, ça claque"

    goods, bads = [], []
    if tide and tide.get("breaker") == "glissante":
        goods.append("marée OK (ça déroule)")
    if wind["factor"] >= 0.7:
        goods.append("offshore propre")
    elif wind["factor"] < 0.5:
        bads.append("onshore")
    if char["clean"] >= 0.7:
        goods.append("houle propre")
    elif char["clean"] < 0.45:
        bads.append("mer du vent (mou)")
    if sdir["factor"] < 0.45:
        bads.append("mal orienté")

    if score >= 4:
        base = "petit mais ça se surfe" if hb < lv["lo"] else "surfable"
        return f"{base} — {', '.join(goods)}" if goods else base
    return ", ".join(bads) if bads else "conditions faibles"


def _overall_label(score: float) -> str:
    if score < 1.5:
        return "à oublier"
    if score < 3:
        return "petit / molasson"
    if score < 5:
        return "surfable, sans plus"
    if score < 6.5:
        return "sympa"
    if score < 8:
        return "bien !"
    return "gros day"


# --------------------------------------------------------------------------
# 7. MOTEUR D'EXPLICATION EN LANGAGE NATUREL — le cœur de ce que tu veux
# --------------------------------------------------------------------------

def build_explanation(score, label, c: Conditions, char, wind, sdir, power, spot, tide=None) -> str:
    """Construit un paragraphe qui explique POURQUOI c'est comme ça."""
    parts = []

    # Verdict
    parts.append(f"**{label.capitalize()}** (note {score}/10).")

    # Le facteur dominant / limitant
    facteurs = {
        "propreté houle": char["clean"],
        "vent": wind["factor"],
        "orientation": sdir["factor"],
    }
    if tide and tide.get("breaker") and tide.get("factor") is not None:
        facteurs["marée"] = tide["factor"]
    limitant = min(facteurs, key=facteurs.get)

    # Énergie
    parts.append(
        f"Houle de {c.swell_h:.1f} m à {c.swell_period:.0f} s → "
        f"puissance ≈ {power:.0f} kW/m. {char['why'].capitalize()}."
    )

    # Mer du vent parasite
    if c.wind_wave_h and c.swell_h and c.wind_wave_h > 0.6 * c.swell_h:
        parts.append(
            f"⚠️ Mer du vent importante ({c.wind_wave_h:.1f} m) qui vient désorganiser la houle."
        )

    # Vent
    parts.append(f"Vent : {wind['why']}.")

    # Orientation
    parts.append(f"Direction : {sdir['why']}.")

    # Marée / type de déferlante
    if tide and tide.get("breaker"):
        parts.append(f"Marée : {tide['why']}.")

    # Facteur limitant explicite
    diagnostic = {
        "propreté houle": "Le point faible, c'est la période (mer du vent) : même hauteur, mais peu d'énergie et mou.",
        "vent": "Le point faible, c'est le vent qui dégrade la surface.",
        "orientation": "Le point faible, c'est l'orientation : la houle n'entre pas bien dans ce spot.",
        "marée": "Le point faible, c'est la marée : à ce niveau d'eau la vague casse mal (shorebreak qui dumpe ou trop molle).",
    }
    if score < 6.5:
        parts.append(diagnostic[limitant])

    return " ".join(parts)


def best_window(evals: list[Evaluation], day_start=7, day_end=21) -> Evaluation | None:
    """Meilleur créneau de la journée (heures de jour)."""
    daylight = [e for e in evals if day_start <= int(e.time[11:13]) <= day_end]
    pool = daylight or evals
    return max(pool, key=lambda e: e.score) if pool else None
