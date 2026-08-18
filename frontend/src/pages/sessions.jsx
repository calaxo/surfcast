import { useEffect, useState } from 'react'
import { useApp } from '@/store'
import { getSessions } from '@/api'
import { fmtDateFull, mdBold } from '@/lib/format'

const arrow = (d) =>
  `<span style="display:inline-block;transform:rotate(${d}deg)">↓</span> ${Math.round(d)}°`

const agreeColor = (a) =>
  a === "d'accord" ? '#37d67a' : a === 'écart moyen' ? '#f6c945' : '#ff6b6b'

export default function Sessions() {
  const { model } = useApp()
  const [data, setData] = useState(null)

  useEffect(() => {
    getSessions(model).then(setData)
  }, [model])

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

      <div className="card my-3.5">
        <b className="text-accent">Ce que la vérif révèle déjà</b>
        <br />
        Le modèle a <b className="text-accent">bien vu le vent</b> les deux fois (offshore
        fin mai, onshore le 18/07) — c'est exactement ta règle. Mais son{' '}
        <b className="text-accent">score brut sous-note les petites houles propres</b> :
        pour ton niveau, <b className="text-accent">petit + offshore = super</b>, même si
        l'énergie physique est faible. → prochaine étape : recalibrer le score en donnant
        plus de poids au vent quand c'est petit.
      </div>
    </div>
  )
}
