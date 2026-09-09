import { useWidth } from '@/lib/useWidth'
import { scoreColor } from '@/lib/format'

// Courbe de marée du jour + ce que le modèle en pense, heure par heure.
// Une sinusoïde seule ne dit pas QUAND aller à l'eau ; ici on superpose la bande de
// score horaire (vert = vas-y), la nuit, les heures de shorebreak, "maintenant" et ta
// session — la marée devient une réponse, pas une décoration.

const hm = (t) => {
  const [h, m] = String(t).split(':').map(Number)
  return h + (m || 0) / 60
}

// Catmull-Rom → Bézier : une courbe lisse à partir de points horaires.
function smoothPath(P) {
  if (P.length < 2) return ''
  let d = `M${P[0].x},${P[0].y}`
  for (let i = 0; i < P.length - 1; i++) {
    const p0 = P[i - 1] || P[i]
    const p1 = P[i]
    const p2 = P[i + 1]
    const p3 = P[i + 2] || p2
    const c1x = p1.x + (p2.x - p0.x) / 6
    const c1y = p1.y + (p2.y - p0.y) / 6
    const c2x = p2.x - (p3.x - p1.x) / 6
    const c2y = p2.y - (p3.y - p1.y) / 6
    d += ` C${c1x},${c1y} ${c2x},${c2y} ${p2.x},${p2.y}`
  }
  return d
}

export default function TideChart({ hours, tides, daylight, sessions, isToday, bestTime }) {
  const [ref, W] = useWidth(360)
  const pts = hours
    .map((e) => ({
      h: +e.time.slice(11, 13),
      v: e.drivers?.maree?.level,
      s: e.score,
      sb: !!e.drivers?.maree?.shorebreak,
    }))
    .filter((p) => p.v != null)
  if (pts.length < 3) return null

  const H = 132
  const L = 6, R = 6, T = 24, B = 36
  const vs = pts.map((p) => p.v)
  const vmin = Math.min(...vs), vmax = Math.max(...vs)
  const X = (h) => L + (h / 23) * (W - L - R)
  const Y = (v) => T + (1 - (v - vmin) / (vmax - vmin || 1)) * (H - T - B)
  const P = pts.map((p) => ({ x: X(p.h), y: Y(p.v) }))
  const line = smoothPath(P)
  const area = `${line} L${P[P.length - 1].x},${H - B} L${P[0].x},${H - B} Z`
  const [lo, hi] = daylight?.surf_light || []
  const now = new Date()
  const nowH = now.getHours() + now.getMinutes() / 60
  const slot = (W - L - R) / 23
  const clampX = (x) => Math.max(30, Math.min(W - 30, x))
  const bandY = H - B + 8

  return (
    <div ref={ref} className="w-full min-w-0">
      <svg width={W} height={H} className="block" style={{ overflow: 'visible' }} role="img"
           aria-label="Courbe de marée du jour avec le score heure par heure">
        {/* nuit : avant l'aube civile / après le crépuscule civil */}
        {lo && <rect x={X(0)} y={T - 8} width={Math.max(0, X(hm(lo)) - X(0))} height={H - T - B + 8} fill="#06111b" opacity=".6" />}
        {hi && <rect x={X(hm(hi))} y={T - 8} width={Math.max(0, X(23) - X(hm(hi)))} height={H - T - B + 8} fill="#06111b" opacity=".6" />}

        {/* ta session (plage horaire) */}
        {sessions?.map((s) => {
          if (!s.time_range || !s.time_range.includes('-')) return null
          const [a, b] = s.time_range.split('-')
          return (
            <rect key={s.id} x={X(hm(a))} y={T - 8} width={Math.max(2, X(hm(b)) - X(hm(a)))}
                  height={H - T - B + 8} fill="#ff9f45" opacity=".14" />
          )
        })}

        {/* marée */}
        <path d={area} fill="#38bdf8" opacity=".13" />
        <path d={line} fill="none" stroke="#38bdf8" strokeWidth="2" strokeLinejoin="round" />

        {/* PM / BM */}
        {tides?.events?.map((ev, i) => {
          const isPM = ev.type === 'PM'
          const x = clampX(X(hm(ev.time)))
          // les deux au-dessus de leur extremum : sous un creux on tomberait sur la bande de score
          const y = Y(ev.height) - 8
          return (
            <text key={i} x={x} y={y} fontSize="11" fontWeight="600" textAnchor="middle"
                  fill={isPM ? '#e8f0f7' : '#8aa4bd'}>
              {ev.type} {ev.time}
            </text>
          )
        })}

        {/* bande de score heure par heure (le "quand y aller") */}
        {pts.map((p) => (
          <rect key={p.h} x={X(p.h) - slot / 2} y={bandY} width={slot + 0.6} height={6}
                fill={scoreColor(p.s)} opacity={p.s >= 3.5 ? 0.9 : 0.3} />
        ))}
        {/* shorebreak : marqueur au-dessus de la bande */}
        {pts.filter((p) => p.sb).map((p) => (
          <text key={'sb' + p.h} x={X(p.h)} y={bandY - 2} fontSize="9" textAnchor="middle" fill="#ff6b6b">⚠</text>
        ))}
        {/* meilleur créneau */}
        {bestTime && (
          <text x={X(hm(bestTime))} y={bandY - 2} fontSize="9" textAnchor="middle" fill="#e8f0f7">▲</text>
        )}

        {/* maintenant */}
        {isToday && (
          <line x1={X(nowH)} x2={X(nowH)} y1={T - 8} y2={bandY + 6} stroke="#ff9f45"
                strokeDasharray="3 3" strokeWidth="1.5" />
        )}

        {/* axe des heures */}
        {[0, 6, 12, 18, 23].map((h) => (
          <text key={h} x={X(h)} y={H - 4} fontSize="10" fill="#8aa4bd"
                textAnchor={h === 0 ? 'start' : h === 23 ? 'end' : 'middle'}>
            {h}h
          </text>
        ))}
      </svg>
    </div>
  )
}
