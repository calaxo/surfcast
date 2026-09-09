import { useState } from 'react'
import Gauge from '@/components/Gauge'
import DriverBar from '@/components/DriverBar'
import TideChart from '@/components/TideChart'
import SpotRose from '@/components/SpotRose'
import { fmtDate, mdBold, scoreColor, factorColor } from '@/lib/format'

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

// Niveau de marée horaire → "+1.2 m ↑" (rel. niveau moyen ; la flèche vient de l'état)
function tideCell(m) {
  if (!m || m.level == null) return '—'
  const st = m.state || ''
  const sym = st.includes('pleine') ? 'PM' : st.includes('basse') ? 'BM' : st.includes('montante') ? '↑' : st.includes('descendante') ? '↓' : ''
  return `${m.level > 0 ? '+' : ''}${m.level.toFixed(1)} m ${sym}`
}

export default function DayCard({ day, best, hours, daylight, tides, spotInfo, isPast, isToday, sessions }) {
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

      {/* infos clés en chips (créneau · fenêtre surfable · lumière · énergie · mer) */}
      <div className="flex flex-wrap gap-1.5 mt-2.5">
        <span className="meta">{isPast ? 'ce jour-là' : 'meilleur'} {best.time.slice(11, 16)} · ~{best.wave_h} m</span>
        {win && <span className="meta text-good border-good/30">🏄 surfable {win.from}–{win.to}</span>}
        {daylight?.sunrise && (
          <span className="meta">☀️ {daylight.sunrise}–{daylight.sunset} · lueur {daylight.civil_dusk}</span>
        )}
        {d.energie?.value != null && (
          <span className="meta" title={`flux d'énergie de la houle (∝ H²·T) · ${d.energie.density_kj_m2} kJ/m² en densité`}>
            ⚡ {d.energie.value} kW/m · {d.energie.label}
          </span>
        )}
        {d.mer?.label && (
          <span className="meta" title={d.mer.why}
                style={{ color: factorColor(d.mer.factor), borderColor: factorColor(d.mer.factor) + '55' }}>
            〰 {d.mer.label}
          </span>
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

      {/* Marée + rose du spot : QUAND dans la marée, et d'OÙ viennent houle et vent par
          rapport à la géométrie du spot. Sur mobile la rose passe sous la courbe. */}
      <div className="mt-3 grid gap-3 items-start [grid-template-columns:1fr] sm:[grid-template-columns:1fr_auto]">
        <div className="min-w-0 bg-card2 border border-line rounded-xl px-2 pt-2 pb-1.5">
          <div className="flex items-baseline justify-between gap-2 flex-wrap px-1">
            <span className="text-[11px] text-mut uppercase tracking-wide">Marée · quand y aller</span>
            {tides?.range != null && (
              <span className="text-[11px] text-mut">
                marnage {tides.range} m{tides.amplitude ? ` · ${tides.amplitude}` : ''}
              </span>
            )}
          </div>
          <TideChart
            hours={hours}
            tides={tides}
            daylight={daylight}
            sessions={sessions}
            isToday={isToday}
            bestTime={best.time.slice(11, 16)}
          />
          <div className="px-1 text-[10.5px] text-mut leading-tight">
            bande = note horaire (vif ≥ 3,5) · ▲ meilleur · ⚠ shorebreak
            {isToday ? ' · pointillé = maintenant' : ''}
            {sessions?.length ? ' · fond orange = ta session' : ''}
          </div>
        </div>
        <SpotRose spot={spotInfo} ev={best} />
      </div>

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
          {d.mer?.why && (
            <p className="mb-3 text-[13px] text-mut">〰 <b className="text-ink">{d.mer.label}</b> — {d.mer.why}.</p>
          )}
          {/* le tableau peut dépasser sur mobile → il scrolle dans son cadre, jamais la page */}
          <div className="overflow-x-auto -mx-1 px-1">
            <table className="w-full border-collapse mt-1 text-[13px] whitespace-nowrap">
              <thead>
                <tr className="text-mut">
                  <th className="text-left py-1 px-1.5 font-normal">Heure</th>
                  <th className="text-left py-1 px-1.5 font-normal">Note</th>
                  <th className="text-left py-1 px-1.5 font-normal">Vagues</th>
                  <th className="text-left py-1 px-1.5 font-normal">Houle</th>
                  <th className="text-left py-1 px-1.5 font-normal">Vent</th>
                  <th className="text-left py-1 px-1.5 font-normal" title="flux d'énergie (kW/m)">⚡</th>
                  <th className="text-left py-1 px-1.5 font-normal">Marée</th>
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
                      {e.drivers.houle.h}m @ {e.drivers.houle.periode}s{' '}
                      <span className="text-mut" dangerouslySetInnerHTML={{ __html: arrow(e.drivers.houle.dir ?? 0) }} />
                    </td>
                    <td className="py-1 px-1.5">
                      <span dangerouslySetInnerHTML={{ __html: arrow(e.drivers.vent.dir ?? 0) }} />{' '}
                      {Math.round(e.drivers.vent.speed)}km/h <span className="text-mut">{e.drivers.vent.label}</span>
                    </td>
                    <td className="py-1 px-1.5">{e.drivers.energie?.value}</td>
                    <td className="py-1 px-1.5 text-mut">
                      {tideCell(e.drivers.maree)}
                      {e.drivers.maree?.shorebreak && <span className="text-bad"> ⚠</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
