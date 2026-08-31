import { useState } from 'react'
import Gauge from '@/components/Gauge'
import DriverBar from '@/components/DriverBar'
import { fmtDate, mdBold, scoreColor } from '@/lib/format'

const arrow = (d) =>
  `<span style="display:inline-block;transform:rotate(${d}deg)">↓</span> ${Math.round(d)}°`

// fenêtre où le score est surfable (>= 3.5), CLIPPÉE à la lumière du jour
// (on ne surfe pas dans le noir). surf_light = [aube civile, crépuscule civil].
function surfWindow(hours, daylight) {
  const [lo, hi] = daylight?.surf_light || ['07:00', '21:00']
  const lit = hours.filter((e) => {
    const t = e.time.slice(11, 16)
    return t >= lo && t <= hi
  })
  const ok = lit.filter((e) => e.score >= 3.5)
  if (!ok.length) return null
  return { from: ok[0].time.slice(11, 16), to: ok[ok.length - 1].time.slice(11, 16), n: ok.length }
}

// Confort thermique : volontairement PAS un driver du score (la température de l'eau
// ne change pas la qualité de la vague), donc pas de barre colorée par un facteur —
// juste une puce d'info + une phrase quand il y a quelque chose à dire.
function thermoColor(v) {
  if (v === 'idéal') return 'var(--good)'
  if (v === 'trop froid') return 'var(--bad)'
  return 'var(--ok)'
}

// Un petit accord ressenti (0-5 → /10) vs modèle
function agreeColor(a) {
  return a === "d'accord" ? 'var(--good)' : a === 'écart moyen' ? 'var(--ok)' : 'var(--bad)'
}

export default function DayCard({ day, best, hours, daylight, isPast, isToday, sessions }) {
  const [open, setOpen] = useState(false)
  const d = best.drivers
  const col = scoreColor(best.score)
  const win = surfWindow(hours, daylight)

  // 5 cartes orientées "ce qu'un surfeur regarde" : vague, houle, vent, direction, marée
  const facts = [
    { title: 'Vagues (au bord)', value: `${d.vague.h} m`, label: d.vague.label, factor: d.vague.factor },
    {
      title: 'Houle',
      value: `${d.houle.h} m · ${d.houle.surf_periode ?? d.houle.periode}s`,
      label:
        // Spot abrité : afficher la houle du large sans dire ce qui entre vraiment
        // serait trompeur (4 m au large ≠ 4 m au fond d'une anse).
        (d.houle.abri
          ? `${d.houle.label} · abri ×${d.houle.abri} → ${d.houle.h_spot} m ici`
          : d.houle.secondaire
            ? `${d.houle.label} · + fond ${d.houle.secondaire.h}m@${d.houle.secondaire.periode}s`
            : d.houle.label),
      factor: d.houle.clean,
    },
    { title: 'Vent', value: `${Math.round(d.vent.speed)} km/h`, label: d.vent.label, factor: d.vent.factor },
    { title: 'Orientation', value: arrow(d.houle.dir), label: d.orientation.label, factor: d.orientation.factor },
  ]
  if (d.maree?.breaker) {
    facts.push({
      title: 'Marée',
      value: d.maree.state,
      label: d.maree.label,
      factor: d.maree.factor,
    })
  }
  const rows = hours.filter((e) => +e.time.slice(11, 13) % 3 === 0)

  return (
    <div className={`card shadow-card my-3.5 ${isPast ? 'opacity-70 border-dashed' : ''} ${isToday ? 'border-accent/60 ring-1 ring-accent/20' : ''}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-base capitalize">{fmtDate(day)}</span>
            {isToday && (
              <span className="text-[11px] font-medium px-1.5 py-0.5 rounded-full bg-accent/15 text-accent">
                aujourd'hui
              </span>
            )}
            {isPast && (
              <span className="text-[11px] font-medium px-1.5 py-0.5 rounded-full bg-line text-mut">
                passé
              </span>
            )}
          </div>
          <div className="font-semibold text-[15px] mt-0.5 first-letter:uppercase" style={{ color: col }}>
            {best.label}
          </div>
          <div className="text-mut text-[13px] leading-snug">{best.headline}</div>
        </div>
        <Gauge score={best.score} />
      </div>

      {/* infos clés en chips (créneau · fenêtre surfable · lumière) */}
      <div className="flex flex-wrap gap-1.5 mt-2.5">
        <span className="meta">{isPast ? 'ce jour-là' : 'meilleur'} {best.time.slice(11, 16)} · ~{best.wave_h} m</span>
        {win && <span className="meta text-good border-good/30">🏄 surfable {win.from}–{win.to}</span>}
        {daylight?.sunrise && (
          <span className="meta">☀️ {daylight.sunrise}–{daylight.sunset} · lueur {daylight.civil_dusk}</span>
        )}
        {d.thermique?.water != null && (
          <span
            className="meta"
            style={{ color: thermoColor(d.thermique.verdict), borderColor: thermoColor(d.thermique.verdict) + '55' }}
            title={d.thermique.why}
          >
            🌡️ eau {d.thermique.water}°C
            {d.thermique.felt != null && d.thermique.felt < d.thermique.water &&
              ` (ressenti ${d.thermique.felt}°)`}
            {' · '}{d.thermique.suit} {d.thermique.verdict}
          </span>
        )}
      </div>

      {/* Bandeau réservé aux cas qui COMPTENT : le froid. Une eau trop chaude ne gêne
          pas (il suffit de laisser entrer un peu d'eau), et répéter l'info sur chaque
          carte de la semaine noyait la page. La puce ci-dessus reste, elle, toujours
          visible et suffit pour le cas "trop chaud". */}
      {d.thermique?.water != null &&
        (d.thermique.verdict === 'trop froid' || d.thermique.verdict === 'limite basse') && (
        <div className="text-[13px] leading-snug mt-2 rounded-lg px-3 py-2 border"
             style={{ color: thermoColor(d.thermique.verdict),
                      borderColor: thermoColor(d.thermique.verdict) + '40',
                      background: thermoColor(d.thermique.verdict) + '12' }}>
          🧥 {d.thermique.why}
          {d.thermique.note_vent && <div className="text-mut mt-1">{d.thermique.note_vent}</div>}
        </div>
      )}

      {sessions?.length > 0 && (
        <div className="mt-2.5 space-y-1.5">
          {sessions.map((s) => (
            <div
              key={s.id}
              className="text-[13px] rounded-lg bg-accent/10 border border-accent/25 px-3 py-2"
            >
              🏄 <b>Ta session{s.time_range ? ` ${s.time_range}` : ''}</b> :{' '}
              <span className="text-accent font-semibold">{s.rating_obs}/5</span> · {s.verdict_obs}
              {s.model_mean_score != null && (
                <span className="text-mut">
                  {' '}— modèle {s.model_mean_score}/10 ·{' '}
                  <span style={{ color: agreeColor(s.agreement) }}>{s.agreement}</span>
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="grid gap-2.5 mt-3 [grid-template-columns:repeat(auto-fit,minmax(180px,1fr))]">
        {facts.map((f) => (
          <DriverBar key={f.title} {...f} />
        ))}
      </div>

      <button
        className="text-mut text-[13px] mt-3 hover:text-ink"
        onClick={() => setOpen((o) => !o)}
      >
        {open ? '▾ Masquer le détail' : '▸ Pourquoi ? (détail + heure par heure)'}
      </button>

      {open && (
        <>
          <p
            className="my-3 text-[14px] text-mut"
            dangerouslySetInnerHTML={{ __html: mdBold(best.explanation) }}
          />
          <table className="w-full border-collapse mt-1 text-[13px]">
            <thead>
              <tr className="text-mut">
                <th className="text-left py-1 px-1.5 font-normal">Heure</th>
                <th className="text-left py-1 px-1.5 font-normal">Note</th>
                <th className="text-left py-1 px-1.5 font-normal">Vagues</th>
                <th className="text-left py-1 px-1.5 font-normal">Houle</th>
                <th className="text-left py-1 px-1.5 font-normal">Vent</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((e) => (
                <tr key={e.time} className="border-t border-line">
                  <td className="py-1 px-1.5">{e.time.slice(11, 16)}</td>
                  <td className="py-1 px-1.5">
                    <span
                      className="chip"
                      style={{ background: scoreColor(e.score) + '22', color: scoreColor(e.score) }}
                    >
                      {e.score}
                    </span>
                  </td>
                  <td className="py-1 px-1.5">{e.wave_h} m</td>
                  <td className="py-1 px-1.5">
                    {e.drivers.houle.h}m @ {e.drivers.houle.periode}s
                  </td>
                  <td className="py-1 px-1.5">
                    {Math.round(e.drivers.vent.speed)}km/h {e.drivers.vent.label}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}
