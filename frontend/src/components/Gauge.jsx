import { scoreColor } from '@/lib/format'

// Pastille de score : anneau plein coloré par le tier.
export default function Gauge({ score }) {
  return (
    <div className="gauge" style={{ '--c': scoreColor(score ?? 0) }}>
      <span>{score ?? '—'}</span>
    </div>
  )
}
