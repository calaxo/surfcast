import { useEffect, useRef, useState } from 'react'

// ---- Viz 1 : période -> hauteur déferlante (Komar T^0.4) vs énergie (P ∝ T) ----
function PeriodHeightViz() {
  const H0 = 1.0
  const [T, setT] = useState(10)
  const cv = useRef(null)
  const breakerH = (t) => H0 * 0.56 * Math.pow(H0 / (1.56 * t * t), -0.2)
  const power = (t) => 0.49 * H0 * H0 * t
  const L0 = 1.56 * T * T
  const c = 1.56 * T * 3.6
  const Hb = breakerH(T)
  const P = power(T)
  const gh = (Hb / breakerH(8) - 1) * 100
  const gp = (P / power(8) - 1) * 100

  useEffect(() => {
    const ctx = cv.current.getContext('2d')
    const { width: W, height: Hc } = cv.current
    ctx.clearRect(0, 0, W, Hc)
    const mid = Hc / 2
    const amp = Math.min(85, Hb * 45)
    const wl = Math.max(60, W * (L0 / 400))
    ctx.strokeStyle = '#38bdf8'
    ctx.lineWidth = 2
    ctx.beginPath()
    for (let x = 0; x <= W; x++) {
      const y = mid - amp * Math.sin((2 * Math.PI * x) / wl)
      x ? ctx.lineTo(x, y) : ctx.moveTo(x, y)
    }
    ctx.stroke()
    ctx.fillStyle = '#8aa4bd'
    ctx.font = '12px system-ui'
    ctx.fillText(
      `H₀ (large) = ${H0} m fixe · L₀ = ${Math.round(L0)} m · Hb = ${Hb.toFixed(2)} m · P = ${P.toFixed(1)} kW/m`,
      10,
      18,
    )
  }, [T])

  const Fig = ({ n, l, color }) => (
    <div className="bg-card2 border border-line rounded-xl px-2.5 py-2 text-center">
      <div className="text-lg font-bold" style={color ? { color } : undefined}>
        {n}
      </div>
      <div className="text-[11px] text-mut">{l}</div>
    </div>
  )

  return (
    <div className="card my-3.5">
      <h3 className="text-[15px] font-semibold text-accent mt-0 mb-1.5">
        Même houle au large, période variable : hauteur qui déferle vs énergie
      </h3>
      <p className="text-mut text-[13px]">
        On garde la <b className="text-accent">même houle au large</b> (H₀ = 1 m fixe →
        même énergie <i>par m²</i>) et on change la période. Deux choses grimpent, mais{' '}
        <b className="text-accent">pas au même rythme</b> — c'est là qu'était ta confusion
        sur les 20%.
      </p>
      <label className="block my-2 text-sm">
        Période T = {T} s
        <input
          type="range"
          min="4"
          max="20"
          step="0.5"
          value={T}
          onChange={(e) => setT(+e.target.value)}
          className="w-full accent-accent"
        />
      </label>
      <div className="grid gap-2.5 [grid-template-columns:repeat(auto-fit,minmax(120px,1fr))]">
        <Fig n={`${Math.round(L0)} m`} l="longueur d'onde L₀" />
        <Fig n={`${Math.round(c)} km/h`} l="vitesse de la houle" />
        <Fig n={`${Hb.toFixed(2)} m`} l="hauteur déferlante Hb" />
        <Fig n={`${P.toFixed(1)} kW/m`} l="puissance (énergie)" />
      </div>
      <div className="grid gap-2.5 mt-2.5 [grid-template-columns:repeat(auto-fit,minmax(120px,1fr))]">
        <Fig n={`${gh >= 0 ? '+' : ''}${Math.round(gh)}%`} l="hauteur vs T=8s (∝ T⁰·⁴)" color="#f6c945" />
        <Fig n={`${gp >= 0 ? '+' : ''}${Math.round(gp)}%`} l="énergie vs T=8s (∝ T)" color="#37d67a" />
      </div>
      <canvas ref={cv} width="900" height="200" className="w-full max-w-full bg-card2 rounded-xl mt-2 block" />
      <div className="rulebox">
        🔧 <b className="text-accent">Tes "+20% par seconde"</b> : ça vaut pour
        l'<b className="text-accent">énergie</b> de la houle (P ∝ H²·T), pas pour la
        hauteur qui déferle. La hauteur ne gagne que{' '}
        <b className="text-accent">~+3–4% par seconde</b> (Hb ∝ T⁰·⁴, Komar-Gaughan), mais
        l'<b className="text-accent">énergie livrée explose</b> (~+8–12%/s). D'où : longue
        période = beaucoup plus de <b className="text-accent">jus</b>, un peu plus de{' '}
        <b className="text-accent">taille</b>.
      </div>
    </div>
  )
}

// ---- Viz 2 : groupes de vagues / battements (modulation AM) ----
function WaveGroupsViz() {
  const [dT, setDT] = useState(12)
  const cv = useRef(null)
  useEffect(() => {
    const ctx = cv.current.getContext('2d')
    const { width: W, height: H } = cv.current
    ctx.clearRect(0, 0, W, H)
    const mid = H / 2
    const f1 = 0.06
    const f2 = 0.06 + dT / 1000
    const env = (x) => 70 * Math.abs(Math.cos(Math.PI * (f1 - f2) * x))
    ctx.strokeStyle = '#ff6b6b'
    ctx.lineWidth = 1.5
    for (const sign of [-1, 1]) {
      ctx.beginPath()
      for (let x = 0; x <= W; x++) {
        const y = mid + sign * env(x)
        x ? ctx.lineTo(x, y) : ctx.moveTo(x, y)
      }
      ctx.stroke()
    }
    ctx.strokeStyle = '#38bdf8'
    ctx.lineWidth = 2
    ctx.beginPath()
    for (let x = 0; x <= W; x++) {
      const y = mid - 35 * (Math.sin(2 * Math.PI * f1 * x) + Math.sin(2 * Math.PI * f2 * x))
      x ? ctx.lineTo(x, y) : ctx.moveTo(x, y)
    }
    ctx.stroke()
    ctx.fillStyle = '#8aa4bd'
    ctx.font = '12px system-ui'
    ctx.fillText('bleu = somme des 2 houles · rouge = enveloppe (les sets)', 10, 16)
  }, [dT])

  return (
    <div className="card my-3.5">
      <h3 className="text-[15px] font-semibold text-accent mt-0 mb-1.5">
        Les vagues arrivent en séries (sets) = battements de sinusoïdes
      </h3>
      <p className="text-mut text-[13px]">
        ✅ Ton intuition "modulation AM" est <b className="text-accent">exacte</b> : deux
        trains de houle de fréquences proches → cos·cos = une{' '}
        <b className="text-accent">porteuse</b> rapide × une{' '}
        <b className="text-accent">enveloppe</b> lente. Et comme l'énergie voyage à Cg =
        c/2, elle se regroupe → les grosses arrivent par <b className="text-accent">séries</b>.
      </p>
      <label className="block my-2 text-sm">
        Écart de période entre les deux houles
        <input
          type="range"
          min="1"
          max="30"
          value={dT}
          onChange={(e) => setDT(+e.target.value)}
          className="w-full accent-accent"
        />
      </label>
      <canvas ref={cv} width="900" height="220" className="w-full max-w-full bg-card2 rounded-xl block" />
    </div>
  )
}

// ---- Viz 3 : distribution de Rayleigh ----
function RayleighViz() {
  const cv = useRef(null)
  useEffect(() => {
    const ctx = cv.current.getContext('2d')
    const { width: W, height: H } = cv.current
    const Hs = 2.0
    const sigma = Hs / 2
    const m = 30
    const pdf = (h) => (h / (sigma * sigma)) * Math.exp(-(h * h) / (2 * sigma * sigma))
    const hmax = 6
    let peak = 0
    for (let h = 0; h < hmax; h += 0.02) peak = Math.max(peak, pdf(h))
    const X = (h) => m + (h / hmax) * (W - 2 * m)
    const Y = (p) => H - m - (p / peak) * (H - 2 * m)
    ctx.clearRect(0, 0, W, H)
    ctx.fillStyle = '#38bdf822'
    ctx.beginPath()
    ctx.moveTo(X(0), Y(0))
    for (let h = 0; h <= hmax; h += 0.02) ctx.lineTo(X(h), Y(pdf(h)))
    ctx.lineTo(X(hmax), Y(0))
    ctx.fill()
    ctx.strokeStyle = '#38bdf8'
    ctx.lineWidth = 2
    ctx.beginPath()
    for (let h = 0; h <= hmax; h += 0.02) {
      const x = X(h)
      const y = Y(pdf(h))
      h ? ctx.lineTo(x, y) : ctx.moveTo(x, y)
    }
    ctx.stroke()
    const marks = [
      [Hs * 0.706, 'Hrms', '#8aa4bd'],
      [Hs, 'Hs', '#f6c945'],
      [Hs * 1.27, 'H1/10', '#37d67a'],
      [Hs * 1.8, 'Hmax', '#ff6b6b'],
    ]
    ctx.font = '12px system-ui'
    for (const [h, lab, col] of marks) {
      ctx.strokeStyle = col
      ctx.setLineDash([4, 3])
      ctx.beginPath()
      ctx.moveTo(X(h), Y(0))
      ctx.lineTo(X(h), Y(peak) - 4)
      ctx.stroke()
      ctx.setLineDash([])
      ctx.fillStyle = col
      ctx.fillText(lab, X(h) - 8, Y(peak) - 8)
    }
    ctx.fillStyle = '#8aa4bd'
    ctx.fillText('hauteur des vagues →', W - 150, H - 10)
  }, [])
  return (
    <div className="card my-3.5">
      <canvas ref={cv} width="900" height="220" className="w-full max-w-full bg-card2 rounded-xl block" />
      <p className="text-mut text-[13px] mt-2">
        Aire sous la courbe = probabilité. Les 10% les plus grosses (H₁/₁₀) sont ~27% plus
        hautes que Hs : d'où le fait d'attendre "la bonne série".
      </p>
    </div>
  )
}

// ---- Viz 4 : énergie — kJ/m² vs kW/m, et "à quoi équivaut cette houle à 8 s ?" ----
// Sert à démonter le piège "1 m à 17 s = 4,5 m à 8 s" lu sur un site de report : ce
// chiffre sort d'une énergie ∝ H·λ (faux). La vraie densité est ∝ H², le flux ∝ H²·T.
function EnergyEquivViz() {
  const [H, setH] = useState(1.0)
  const [T, setT] = useState(17)
  const rho = 1025, g = 9.81
  const density = (h) => (rho * g * h * h) / 8 / 1000 // kJ/m²
  const flux = (h, t) => 0.49 * h * h * t // kW/m
  const hb = (h, t) => 0.56 * h * Math.pow(h / (1.56 * t * t), -0.2)
  const P = flux(H, T)
  const Heq = Math.sqrt(P / (0.49 * 8)) // même flux à 8 s
  const Hwrong = (H * T * T) / 64 // ce que donne la "formule" H·λ (λ ∝ T²) à 8 s
  const Fig = ({ n, l, color }) => (
    <div className="bg-card2 border border-line rounded-xl px-2.5 py-2 text-center">
      <div className="text-lg font-bold" style={color ? { color } : undefined}>{n}</div>
      <div className="text-[11px] text-mut">{l}</div>
    </div>
  )
  return (
    <div className="card my-3.5">
      <h3 className="text-[15px] font-semibold text-accent mt-0 mb-1.5">
        À quoi équivaut cette houle… ramenée à 8 s ?
      </h3>
      <div className="grid sm:grid-cols-2 gap-3 my-2 text-sm">
        <label className="block">
          Hauteur H = {H.toFixed(1)} m
          <input type="range" min="0.3" max="4" step="0.1" value={H} onChange={(e) => setH(+e.target.value)} className="w-full accent-accent" />
        </label>
        <label className="block">
          Période T = {T} s
          <input type="range" min="5" max="20" step="1" value={T} onChange={(e) => setT(+e.target.value)} className="w-full accent-accent" />
        </label>
      </div>
      <div className="grid gap-2.5 [grid-template-columns:repeat(auto-fit,minmax(120px,1fr))]">
        <Fig n={`${density(H).toFixed(1)} kJ/m²`} l="densité d'énergie (∝ H², sans T)" />
        <Fig n={`${P.toFixed(1)} kW/m`} l="flux d'énergie (∝ H²·T) — ce qu'on affiche" color="#38bdf8" />
        <Fig n={`${hb(H, T).toFixed(2)} m`} l="hauteur déferlante Hb (Komar)" />
      </div>
      <div className="grid gap-2.5 mt-2.5 [grid-template-columns:repeat(auto-fit,minmax(120px,1fr))]">
        <Fig n={`${Heq.toFixed(2)} m @ 8 s`} l={`même flux · Hb ${hb(Heq, 8).toFixed(2)} m (identique)`} color="#37d67a" />
        <Fig n={`${Hwrong.toFixed(1)} m @ 8 s`} l="avec la formule H·λ (fausse)" color="#ff6b6b" />
      </div>
      <div className="rulebox">
        🔧 <b className="text-accent">Le piège</b> : « 1 m à 17 s ≡ 4,5 m à 8 s » sort d'une énergie
        ∝ H·λ/2 (donc ∝ H·T²). Or l'énergie est en <b className="text-accent">H²</b> et le flux en{' '}
        <b className="text-accent">H²·T</b> : 1 m à 17 s ≡ <b className="text-accent">1,46 m à 8 s</b>,
        et Komar donne la <b className="text-accent">même hauteur déferlante</b> pour les deux
        (~1,9 m) — la cohérence est là. Même erreur pour « +20 % de période = +44 % » : c'est{' '}
        <b className="text-accent">+20 %</b>. Le message de fond reste vrai : la période compte
        autant que la hauteur, pas 3× plus.
      </div>
    </div>
  )
}

const H3 = ({ children }) => (
  <h3 className="text-[15px] font-semibold text-accent mt-5 mb-1.5">{children}</h3>
)

export default function Science() {
  return (
    <div className="mt-4">
      <h2 className="text-lg font-semibold">Pourquoi les vagues sont comme ça — la vraie physique (sourcée)</h2>
      <p className="text-mut text-[13px]">
        Contenu vérifié contre le Coastal Engineering Manual (USACE), Komar &amp; Gaughan
        1972, Longuet-Higgins 1952, Battjes 1974. Détails + sources :{' '}
        <code>docs/physique-vagues-surf.md</code>.
      </p>

      <H3>1. La période fait tout : longueur d'onde ∝ T²</H3>
      <p>En eau profonde, longueur d'onde et vitesse ne dépendent QUE de la période :</p>
      <div className="formula">
        L₀ = g·T²/(2π) ≈ <b className="text-accent">1.56·T²</b> (m) | célérité c₀ = 1.56·T
        (m/s) | vitesse de groupe Cg = c₀/2 ≈ 0.78·T
      </div>
      <div className="rulebox">
        🔧 <b className="text-accent">Correction</b> — "L₀ = 1.28×H×T²" est faux : la
        longueur d'onde ne dépend <b className="text-accent">pas</b> de la hauteur H. Le
        "1.28" est un "1.56" corrompu (= g/2π) et le "×H" vient d'une contamination avec
        une formule d'<b className="text-accent">énergie</b> (où H entre, mais en H²). Ton
        "∝ T²" est <b className="text-accent">juste</b>.
      </div>

      <PeriodHeightViz />

      <H3>2. Houle vs mer du vent</H3>
      <p>
        La <b className="text-accent">houle</b> (tempête lointaine, triée par la dispersion
        — les longues périodes voyagent plus vite et arrivent d'abord) est régulière, faible
        cambrure. La <b className="text-accent">mer du vent</b> (générée localement) est
        courte, raide, désorganisée — <b className="text-accent">ce que tu as eu</b>. Seuils
        (Tp) : <b className="text-accent">&lt;10 s</b> mer du vent,{' '}
        <b className="text-accent">10–13 s</b> houle limite,{' '}
        <b className="text-accent">&gt;14 s</b> houle longue puissante.
      </p>

      <H3>3. Types de déferlement & nombre d'Iribarren — d'où viennent les rouleaux</H3>
      <div className="formula">ξ = tan(β) / √(H/L₀)  (tanβ = pente du fond, H/L₀ = cambrure)</div>
      <table className="w-full border-collapse mt-2.5 text-[13.5px]">
        <thead>
          <tr className="text-mut">
            <th className="text-left py-1.5 px-1.5 font-normal">Type</th>
            <th className="text-left py-1.5 px-1.5 font-normal">ξ₀</th>
            <th className="text-left py-1.5 px-1.5 font-normal">Ce que ça donne</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-t border-line">
            <td className="py-1.5 px-1.5"><b>Glissante</b> (spilling)</td>
            <td className="py-1.5 px-1.5">&lt; 0.5</td>
            <td className="py-1.5 px-1.5">mousse qui glisse, pas de tube. Pente douce + houle raide. Favorisée par l'onshore.</td>
          </tr>
          <tr className="border-t border-line">
            <td className="py-1.5 px-1.5"><b>Plongeante</b> (plunging)</td>
            <td className="py-1.5 px-1.5">0.5 – 3.3</td>
            <td className="py-1.5 px-1.5">🛢️ LE tube. Fond raide et/ou houle longue peu cambrée. Favorisée par l'<b className="text-accent">offshore</b>.</td>
          </tr>
          <tr className="border-t border-line">
            <td className="py-1.5 px-1.5"><b>Gonflante</b> (surging)</td>
            <td className="py-1.5 px-1.5">&gt; 3.3</td>
            <td className="py-1.5 px-1.5">monte/descend sans vraiment casser. Plage très raide + houle très longue.</td>
          </tr>
        </tbody>
      </table>
      <div className="rulebox">
        🏄 <b className="text-accent">Tes beaux rouleaux à la Côte Sauvage</b> : il faut du{' '}
        <b className="text-accent">plongeant</b> = houle <b className="text-accent">longue
        période</b> (petit H/L₀) + <b className="text-accent">vent offshore</b> (de terre,
        qui tient la crête). C'est ta règle de terrain, et voilà la physique : l'offshore ne
        "fait" pas la vague, il l'empêche de s'effondrer trop tôt.
      </div>

      <H3>4. La marée</H3>
      <p>
        La marée change la <b className="text-accent">profondeur h</b> → déplace le point de
        déferlement et fait "sentir" à la vague une{' '}
        <b className="text-accent">pente locale différente</b> (donc un ξ différent → la
        même houle peut être molle à une marée et creuse à une autre). Trop d'eau (haute) =
        vagues grasses ; trop peu (basse) = ça ferme/vidange ;{' '}
        <b className="text-accent">mi-marée montante</b> = souvent l'optimum sur un beach
        break.
      </p>

      <WaveGroupsViz />

      <H3>5. Toutes les vagues n'ont pas la même taille : loi de Rayleigh</H3>
      <p>
        ✅ Tu avais raison : les hauteurs suivent une{' '}
        <b className="text-accent">distribution de Rayleigh</b> (pas normale, pas Poisson).
        L'élévation de la surface, elle, est gaussienne ; c'est la <i>hauteur</i>{' '}
        crête-à-creux qui est Rayleigh (Longuet-Higgins 1952).
      </p>
      <div className="formula">
        Hs = moyenne du <b className="text-accent">tiers</b> le plus haut = H₁/₃ | H₁/₁₀ ≈{' '}
        <b className="text-accent">1.27·Hs</b> | Hmax ≈ 1.86–2.0·Hs (sur 1000–3000 vagues)
      </div>
      <RayleighViz />

      <H3>6. Sous l'eau : mouvement orbital</H3>
      <p>
        En eau profonde l'eau décrit des <b className="text-accent">orbites circulaires</b>{' '}
        dont le rayon décroît en <b className="text-accent">e^(k·z)</b> : à une demi-longueur
        d'onde (z = −L/2) il ne reste que <b className="text-accent">e^(−π) ≈ 4%</b> du
        mouvement (la "base des vagues"). Près du bord les orbites s'aplatissent et{' '}
        <b className="text-accent">touchent le fond</b> → shoaling, réfraction, déferlement.
        Une houle longue "sent" le fond plus au large → déferle plus gros.
      </p>

      <H3>7. Comment font les experts (la checklist)</H3>
      <ol className="list-decimal ml-5 space-y-1 text-[14.5px]">
        <li><b className="text-accent">Un report tout fait</b> pour la tendance.</li>
        <li><b className="text-accent">Cartes de pression</b> : repérer la dépression atlantique qui génère la houle (isobares serrées = vent fort ; anticyclone = calme/offshore mais pas de houle).</li>
        <li><b className="text-accent">Cartes de période/énergie</b> : longue période = groundswell puissant. Temps de trajet ≈ distance / (1.5×Tp nœuds).</li>
        <li><b className="text-accent">Bouées houlographes</b> (CANDHIS) : prévu vs mesuré — exactement ce que fait l'onglet "vérité terrain".</li>
        <li><b className="text-accent">Webcams</b> : la vérité que les modèles ne donnent pas.</li>
        <li><b className="text-accent">Spectre directionnel</b> : pic étroit = houle propre d'une tempête ; tache large = mer du vent.</li>
      </ol>

      <H3>8. L'énergie : kJ, kW/m — et le piège du « 4,5 m »</H3>
      <p>
        Les sites de report parlent d'« énergie » en kJ, sans toujours dire de quoi. Il y a
        deux grandeurs, et elles ne disent pas la même chose :
      </p>
      <div className="formula">
        densité E = ρ·g·H²/8 (kJ/m²) — ne dépend <b className="text-accent">que de H</b> |
        flux P = E·Cg ≈ <b className="text-accent">0,49·H²·T</b> (kW/m) — ce qui arrive sur la
        plage chaque seconde
      </div>
      <p>
        Le <b className="text-accent">flux</b> est le bon indicateur de « jus » : une seconde de
        période en plus, c'est ~+10 % de flux autour de 10 s (∝ T), et ~+3-4 % de hauteur
        déferlante (∝ T⁰·⁴). C'est lui qu'on affiche (⚡ kW/m) sur chaque carte-jour, et c'est
        sur lui qu'on apprend, spot par spot, la plage de <b className="text-accent">tes</b>{' '}
        bonnes sessions (onglet Sessions) — plutôt que de deviner « ça marche à partir de
        100 kJ ».
      </p>
      <EnergyEquivViz />

      <H3>9. Mer « rangée » ou « chantier » : l'étalement directionnel</H3>
      <p>
        Une houle née d'une seule tempête lointaine arrive <b className="text-accent">triée</b>{' '}
        : une direction, une période → des lignes propres, des pics prévisibles. Quand deux
        trains de houle de directions différentes se croisent, ou que la mer du vent locale
        s'ajoute, les crêtes se croisent, les vagues ferment et se dédoublent : c'est le{' '}
        <b className="text-accent">spectre directionnel étalé</b> des pros. Open-Meteo ne fournit
        pas l'étalement, mais on l'approche avec ce qu'on a :
      </p>
      <div className="formula">
        part d'énergie de la mer du vent = H²(mer du vent) / H²(total) | écart de direction
        entre houle primaire et secondaire (quand la 2ᵉ pèse ≥ 40 % de la 1ʳᵉ)
      </div>
      <div className="rulebox">
        〰 <b className="text-accent">Bien rangée</b> : une houle dominante, une direction.{' '}
        <b className="text-accent">Un peu mélangée</b> : houle + mer du vent se partagent
        l'énergie. <b className="text-accent">Chantier</b> : mer croisée, pics qui se croisent,
        vagues qui ferment. Indicateur <i>informatif</i> pour l'instant : il n'entre pas dans la
        note tant qu'il n'est pas calibré sur des sessions « mer croisée » loguées.
      </div>

      <H3>10. Bancs de sable et baïnes : pourquoi le même spot change d'une semaine à l'autre</H3>
      <p>
        Sur un beach break, la vague casse là où le fond <b className="text-accent">remonte
        vite</b>. Ce relief est fait par l'eau elle-même : là où ça casse fort, la mer est
        « poussée » plus haut (set-up), l'eau s'évacue par les points faibles → courants
        d'alimentation → un <b className="text-accent">chenal</b> se creuse (la baïne) et le
        sable arraché va former le <b className="text-accent">banc</b> à côté. La boucle
        s'auto-entretient à chaque marée et chaque train de houle : un banc « vit » quelques
        semaines, le pic se déplace, puis le chenal s'élargit et tout se dilue. Le banc idéal a
        une <b className="text-accent">marche</b> franche devant lui — d'où un pic bien identifié
        juste à côté du courant.
      </p>
      <div className="rulebox">
        🔎 <b className="text-accent">Ce que le modèle ne voit pas</b> : sa maille fait 5-10 km,
        il ne connaît pas le banc de cette semaine. La note dit si la houle, le vent et la
        marée sont bons ; <b className="text-accent">où</b> ça casse le mieux, c'est ton
        observation depuis la dune (10 min avant de te changer) et tes sessions loguées — c'est
        exactement pour ça que la vérité terrain compte autant que la prévision. Rappel utile :
        à basse mer de vive-eau, les baïnes se vident → backwash (déjà signalé dans l'explication
        du jour), et la baïne est aussi ta sortie au large la plus économique quand tu sais la
        lire.
      </div>
    </div>
  )
}
