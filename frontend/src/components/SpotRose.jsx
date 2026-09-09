// Rose du spot : la GÉOMÉTRIE du spot (terre, fenêtre de houle, secteur offshore) et,
// par-dessus, d'où viennent la houle et le vent à l'heure choisie. D'un coup d'œil :
// la houle rentre-t-elle dans la fenêtre ? le vent est-il de terre ?
// Convention météo : les directions sont "d'où ça vient" ; les flèches partent donc du
// bord (côté d'origine) et pointent vers le centre (le spot).

const rad = (deg) => ((deg - 90) * Math.PI) / 180 // 0° = Nord en haut, sens horaire
const pt = (cx, cy, r, deg) => [cx + r * Math.cos(rad(deg)), cy + r * Math.sin(rad(deg))]

// Secteur d'anneau entre deux azimuts (sens horaire de a vers b).
function ring(cx, cy, r0, r1, a, b) {
  let span = (((b - a) % 360) + 360) % 360
  if (span === 0) span = 359.9
  const large = span > 180 ? 1 : 0
  const [x0, y0] = pt(cx, cy, r1, a)
  const [x1, y1] = pt(cx, cy, r1, a + span)
  const [x2, y2] = pt(cx, cy, r0, a + span)
  const [x3, y3] = pt(cx, cy, r0, a)
  return `M${x0},${y0} A${r1},${r1} 0 ${large} 1 ${x1},${y1} L${x2},${y2} A${r0},${r0} 0 ${large} 0 ${x3},${y3} Z`
}

function Arrow({ cx, cy, from, len, color, width = 3, dash }) {
  if (from == null || !len) return null
  const [x0, y0] = pt(cx, cy, len, from) // origine (d'où ça vient)
  const [x1, y1] = pt(cx, cy, 9, from) // tête, près du spot
  const ux = (x1 - x0) / Math.hypot(x1 - x0, y1 - y0)
  const uy = (y1 - y0) / Math.hypot(x1 - x0, y1 - y0)
  const hw = width * 1.6
  const hl = width * 2.6
  const bx = x1 - ux * hl, by = y1 - uy * hl
  const head = `${x1},${y1} ${bx - uy * hw},${by + ux * hw} ${bx + uy * hw},${by - ux * hw}`
  return (
    <g>
      <line x1={x0} y1={y0} x2={bx} y2={by} stroke={color} strokeWidth={width}
            strokeLinecap="round" strokeDasharray={dash} />
      <polygon points={head} fill={color} />
    </g>
  )
}

export default function SpotRose({ spot, ev, size = 136 }) {
  if (!spot || !ev) return null
  const cx = size / 2, cy = size / 2
  const R = size / 2 - 8
  const facing = spot.beach_facing ?? 270
  const [wlo, whi] = spot.swell_window || [facing - 45, facing + 45]
  const off = spot.offshore_dir
  const h = ev.drivers?.houle || {}
  const v = ev.drivers?.vent || {}
  const sec = h.secondaire
  const swellLen = 14 + Math.min(1, (h.h || 0) / 2.5) * (R - 22)
  const secLen = sec ? 14 + Math.min(1, (sec.h || 0) / 2.5) * (R - 22) : 0
  const windLen = 14 + Math.min(1, (v.speed || 0) / 40) * (R - 22)
  const card = [['N', 0], ['E', 90], ['S', 180], ['O', 270]]

  return (
    <div className="shrink-0 flex flex-col items-center" style={{ width: size }}>
      <svg width={size} height={size} role="img" aria-label="Rose du spot : houle, vent, fenêtre">
        {/* mer (fond) et terre (demi-disque derrière la plage) */}
        <circle cx={cx} cy={cy} r={R} fill="#0e1b28" stroke="#22384f" />
        <path d={ring(cx, cy, 0, R, facing + 90, facing + 270)} fill="#1d3247" />
        {/* fenêtre de houle (anneau extérieur, vert) */}
        <path d={ring(cx, cy, R - 6, R, wlo, whi)} fill="#37d67a" opacity=".55" />
        {/* secteur offshore ±45° (anneau intérieur, cyan) */}
        {off != null && <path d={ring(cx, cy, R - 12, R - 7, off - 45, off + 45)} fill="#38bdf8" opacity=".5" />}
        {/* points cardinaux */}
        {card.map(([l, a]) => {
          const [x, y] = pt(cx, cy, R - 19, a)
          return (
            <text key={l} x={x} y={y + 3.5} fontSize="9" textAnchor="middle" fill="#8aa4bd">{l}</text>
          )
        })}
        {/* houle secondaire (fine, pointillée), houle dominante, vent */}
        {sec && <Arrow cx={cx} cy={cy} from={sec.dir} len={secLen} color="#38bdf8" width={1.6} dash="3 3" />}
        <Arrow cx={cx} cy={cy} from={h.dir} len={swellLen} color="#38bdf8" width={3.2} />
        <Arrow cx={cx} cy={cy} from={v.dir} len={windLen} color="#ff9f45" width={2.4} />
        <circle cx={cx} cy={cy} r={3.5} fill="#e8f0f7" />
      </svg>
      <div className="text-[10.5px] leading-tight text-mut text-center mt-0.5">
        <div><span className="text-accent">━</span> houle {h.h} m · {Math.round(h.dir ?? 0)}°</div>
        <div><span className="text-sunset">━</span> vent {Math.round(v.speed ?? 0)} km/h · {Math.round(v.dir ?? 0)}°</div>
        <div className="opacity-80"><span className="text-good">▮</span> fenêtre houle · <span className="text-accent">▮</span> offshore</div>
      </div>
    </div>
  )
}
