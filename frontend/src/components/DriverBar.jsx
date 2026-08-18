import { factorColor } from '@/lib/format'

// Une "carte facteur" (Énergie / Houle / Vent / Orientation) avec barre de niveau.
export default function DriverBar({ title, value, label, factor }) {
  return (
    <div className="bg-card2 border border-line rounded-xl px-3 py-2.5">
      <div className="text-[11px] text-mut uppercase tracking-wide">{title}</div>
      <div className="text-[15px] mt-0.5" dangerouslySetInnerHTML={{ __html: value }} />
      <div className="text-[13px] text-mut">{label}</div>
      <div className="h-1.5 rounded bg-[#1d3247] mt-2 overflow-hidden">
        <div
          className="h-full rounded"
          style={{ width: `${Math.round(factor * 100)}%`, background: factorColor(factor) }}
        />
      </div>
    </div>
  )
}
