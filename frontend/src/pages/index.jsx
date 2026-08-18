import { useEffect, useState } from 'react'
import { useApp } from '@/store'
import { getForecast, getSessions } from '@/api'
import { daysOf, bestOfDay } from '@/lib/format'
import DayCard from '@/components/DayCard'

export default function Forecast() {
  const { spot, model, level, config } = useApp()
  const [data, setData] = useState(null)
  const [sessByDate, setSessByDate] = useState({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!spot) return
    setLoading(true)
    getForecast(spot, model, level)
      .then(setData)
      .finally(() => setLoading(false))
  }, [spot, model, level])

  // Sessions loguées → indexées par date (pour comparer ressenti vs modèle sur les jours passés)
  useEffect(() => {
    getSessions()
      .then((s) => {
        const map = {}
        for (const v of s.verifications || []) {
          if (v.spot !== spot) continue
          ;(map[v.date] ||= []).push(v)
        }
        setSessByDate(map)
      })
      .catch(() => setSessByDate({}))
  }, [spot])

  if (loading || !data)
    return (
      <div className="flex items-center justify-center gap-2 text-mut py-16">
        <span className="inline-block w-2 h-2 rounded-full bg-accent animate-ping" />
        Chargement des données de houle…
      </div>
    )
  const evals = data.evals || []
  if (!evals.length) return <div className="text-mut py-10 text-center">Pas de données pour ce spot.</div>

  const spotInfo = config?.spots?.[spot]
  const reports = spotInfo?.reports || {}
  const affluence = spotInfo?.affluence
  const ecoles = spotInfo?.ecoles || []

  return (
    <div>
      {spotInfo && (
        <div className="card !py-3 mt-3 mb-1 text-[13px]">
          <div className="text-mut leading-snug">
            <span className="text-ink font-semibold">{spotInfo.region}</span>
            {spotInfo.notes ? ` · ${spotInfo.notes}` : ''}
          </div>

          {Object.keys(reports).length > 0 && (
            <div className="flex gap-1.5 flex-wrap mt-2 items-center">
              <span className="text-mut text-[12px]">Comparer :</span>
              {Object.entries(reports).map(([name, url]) => (
                <a
                  key={name}
                  href={url}
                  target="_blank"
                  rel="noreferrer"
                  className="chip bg-card2 border border-line !text-ink hover:border-accent transition-colors"
                >
                  {name} ↗
                </a>
              ))}
            </div>
          )}

          {(affluence?.conseil || ecoles.length > 0) && (
            <div className="mt-2.5 pt-2.5 border-t border-line space-y-1 text-[12.5px]">
              {affluence?.conseil && (
                <div className="text-mut">
                  <span className="text-ink">👥 Affluence</span> — {affluence.conseil}
                  {affluence.creneaux_charges?.length > 0 && ` (chargé ${affluence.creneaux_charges.join(', ')})`}
                </div>
              )}
              {ecoles.length > 0 && (
                <div className="text-mut">
                  <span className="text-ink">🏫 Écoles</span> —{' '}
                  {ecoles.map((e, i) => (
                    <span key={e.nom}>
                      {i > 0 && ' · '}
                      <a href={e.url} target="_blank" rel="noreferrer" className="!text-accent hover:underline">
                        {e.nom}
                      </a>
                      {e.note ? ` (${e.note})` : ''}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
      {daysOf(evals).map((day) => {
        const hours = evals.filter((e) => e.time.slice(0, 10) === day)
        const today = new Date().toLocaleDateString('en-CA')  // YYYY-MM-DD local
        return (
          <DayCard
            key={day}
            day={day}
            best={bestOfDay(evals, day)}
            hours={hours}
            daylight={data.daylight?.[day]}
            isPast={day < today}
            isToday={day === today}
            sessions={sessByDate[day]}
          />
        )
      })}
    </div>
  )
}
