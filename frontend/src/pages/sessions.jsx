import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useApp } from '@/store'
import { getSessions } from '@/api'
import { fmtDateFull, mdBold } from '@/lib/format'

const arrow = (d) =>
  `<span style="display:inline-block;transform:rotate(${d}deg)">↓</span> ${Math.round(d)}°`

const agreeColor = (a) =>
  a === "d'accord" ? '#37d67a' : a === 'écart moyen' ? '#f6c945' : '#ff6b6b'

export default function Sessions() {
  const { model, me } = useApp()
  const [data, setData] = useState(null)

  useEffect(() => {
    if (!me.owner) return
    getSessions(model)
      .then(setData)
      .catch(() => setData({ verifications: [], rules: [], energy_by_spot: [] }))
  }, [model, me.owner])

  if (!me.checked) return <div className="text-mut py-8">Chargement…</div>
  if (!me.owner)
    return (
      <div className="text-mut py-10 text-center text-sm">
        Page personnelle. <Link to="/connexion">Se connecter</Link>
      </div>
    )
  if (!data) return <div className="text-mut py-8">Chargement du journal + hindcast…</div>

  return (
    <div>
      <h2 className="text-lg font-semibold mt-6 mb-1">
        Vérité terrain : ce que TU as vu vs ce que le modèle disait
      </h2>
      <p className="text-mut text-[13px]">
        Pour chaque session loguée, on récupère ce que le modèle prévoyait ce jour-là
        (hindcast) et on compare à ton ressenti. C'est ça qui dit quel modèle croire sur
        ton spot.
      </p>

      {data.rules?.map((r, i) => (
        <div key={i} className="rulebox">
          📌 <b className="text-accent">Règle apprise</b> — {r.rule}
          <br />
          <span className="text-mut text-[13px]">{r.source}</span>
        </div>
      ))}

      {data.verifications?.map((v) => (
        <div key={v.id} className="card my-3.5">
          <div className="flex justify-between items-center gap-3 flex-wrap">
            <div className="font-semibold capitalize">{fmtDateFull(v.date)}</div>
            <div className="text-[13px] text-mut">
              accord modèle/ressenti :{' '}
              <span className="font-semibold" style={{ color: agreeColor(v.agreement) }}>
                {v.agreement || '—'}
              </span>
            </div>
          </div>

          <div className="flex gap-4 flex-wrap items-start mt-2.5">
            <div className="flex-1 min-w-[240px]">
              <div className="text-mut text-[12px] uppercase tracking-wide">Ce que tu as vu</div>
              <div className="text-xl font-bold">
                {v.rating_obs}/5 <span className="text-mut text-sm font-normal">{v.verdict_obs}</span>
              </div>
              <div className="mt-1">
                <span
                  className="chip"
                  style={
                    v.observed.onshore
                      ? { background: '#ff6b6b22', color: '#ff6b6b' }
                      : { background: '#37d67a22', color: '#37d67a' }
                  }
                >
                  {v.observed.wind_txt}
                </span>
              </div>
              <div className="mt-1.5">🌊 {v.observed.size_txt} · {v.observed.break_txt}</div>
              <div className="text-mut text-[13px] mt-1.5">{v.notes}</div>
            </div>

            <div className="flex-1 min-w-[240px]">
              <div className="text-mut text-[12px] uppercase tracking-wide">
                Ce que le modèle disait
              </div>
              {v.model_available ? (
                <>
                  <div className="text-xl font-bold">
                    {v.model_best_score}/10{' '}
                    <span className="text-mut text-sm font-normal">
                      (meilleur {v.model_best_time})
                    </span>
                  </div>
                  <div
                    dangerouslySetInnerHTML={{
                      __html: `Vent modèle : ${arrow(v.model_wind_dir)} <b class="text-accent">${v.model_wind_label}</b>`,
                    }}
                  />
                  <div
                    className="text-[13.5px] mt-1.5"
                    dangerouslySetInnerHTML={{ __html: mdBold(v.model_explanation) }}
                  />
                </>
              ) : (
                <div className="text-mut">{v.note_model}</div>
              )}
            </div>
          </div>
        </div>
      ))}

      <Bilan verifs={data.verifications || []} />
      <EnergyBySpot rows={data.energy_by_spot || []} />
    </div>
  )
}

// Bilan chiffré, recalculé à chaque fois (plus de texte figé qui vieillit mal).
function Bilan({ verifs }) {
  const ok = verifs.filter((v) => v.model_available)
  if (!ok.length) return null
  const agree = ok.filter((v) => v.agreement === "d'accord").length
  const gaps = ok.map((v) => v.gap).filter((g) => g != null)
  const meanAbs = gaps.length ? gaps.reduce((a, g) => a + Math.abs(g), 0) / gaps.length : null
  const bias = gaps.length ? gaps.reduce((a, g) => a + g, 0) / gaps.length : null
  return (
    <div className="card my-3.5 text-[14px]">
      <b className="text-accent">Bilan</b> — sur {ok.length} sessions comparées, le modèle est{' '}
      <b className="text-good">d'accord {agree} fois</b>
      {meanAbs != null && <> ; écart moyen {meanAbs.toFixed(1)} pt</>}
      {bias != null && (
        <>
          , biais {bias > 0 ? '+' : ''}{bias.toFixed(1)}{' '}
          <span className="text-mut">({bias > 0.3 ? 'un peu trop optimiste' : bias < -0.3 ? 'un peu trop pessimiste' : 'pas de biais net'})</span>
        </>
      )}
      .
    </div>
  )
}

// Plage d'énergie (kW/m) des bonnes vs mauvaises sessions, par spot. Quand les deux
// plages se chevauchent, c'est une info en soi : l'énergie ne fait pas la session, ce
// sont le vent et la marée qui tranchent.
function EnergyBySpot({ rows }) {
  const has = rows.filter((r) => r.good || r.bad)
  if (!has.length) return null
  const fmt = (r) => (r ? `${r[0]}–${r[1]} kW/m` : '—')
  const overlap = (r) => r.good && r.bad && r.bad[1] >= r.good[0] && r.good[1] >= r.bad[0]
  return (
    <div className="card my-3.5">
      <b className="text-accent">⚡ Ton énergie de kiff, spot par spot</b>
      <p className="text-mut text-[13px] mt-1">
        Flux d'énergie de la houle (kW/m, ∝ H²·T) pendant tes sessions, reconstruit par le
        modèle. Les pros disent « tel spot marche à partir de X » ; ici c'est mesuré sur{' '}
        <i>tes</i> sessions, et la plage se resserre au fil du journal.
      </p>
      <div className="grid gap-2 mt-2 [grid-template-columns:repeat(auto-fit,minmax(240px,1fr))]">
        {has.map((r) => (
          <div key={r.spot} className="bg-card2 border border-line rounded-xl px-3 py-2.5 text-[13.5px]">
            <div className="font-semibold">{r.name}</div>
            <div className="mt-1">
              <span className="text-good">●</span> bonnes (≥ 4/5) : <b>{fmt(r.good)}</b>{' '}
              <span className="text-mut">(n={r.n_good})</span>
            </div>
            <div>
              <span className="text-bad">●</span> nulles (≤ 2/5) : <b>{fmt(r.bad)}</b>{' '}
              <span className="text-mut">(n={r.n_bad})</span>
            </div>
            {overlap(r) && (
              <div className="text-mut text-[12.5px] mt-1.5">
                Les plages se chevauchent → ici l'énergie seule ne fait pas la session : c'est
                le vent et la marée (shorebreak) qui tranchent.
              </div>
            )}
            {!r.good && r.bad && (
              <div className="text-mut text-[12.5px] mt-1.5">
                Que des sessions nulles pour l'instant, avec de l'énergie : le problème n'était
                pas la houle (marée haute de vive-eau → shorebreak).
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
