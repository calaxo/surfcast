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

  if (loading || !data) return <div className="text-mut py-8">Chargement des données de houle…</div>
  const evals = data.evals || []
  if (!evals.length) return <div className="text-mut py-8">Pas de données.</div>

  const spotInfo = config?.spots?.[spot]
  const reports = spotInfo?.reports || {}
  const affluence = spotInfo?.affluence
  const ecoles = spotInfo?.ecoles || []

  return (
    <div>
      {spotInfo && (
        <p className="text-mut text-[13px] mt-3">
          {spotInfo.region} · {spotInfo.notes}
        </p>
      )}
      {Object.keys(reports).length > 0 && (
        <div className="flex gap-2 flex-wrap mt-2 items-center">
          <span className="text-mut text-[12px]">Comparer sur :</span>
          {Object.entries(reports).map(([name, url]) => (
            <a
              key={name}
              href={url}
              target="_blank"
              rel="noreferrer"
              className="chip bg-card border border-line !text-ink hover:border-accent"
            >
              {name} ↗
            </a>
          ))}
        </div>
      )}
      {(affluence || ecoles.length > 0) && (
        <div className="card my-3 !py-2.5 text-[13px]">
          {affluence?.conseil && (
            <div>
              👥 <b>Affluence</b> : {affluence.conseil}
              {affluence.creneaux_charges?.length > 0 && (
                <span className="text-mut"> (chargé {affluence.creneaux_charges.join(', ')})</span>
              )}
            </div>
          )}
          {ecoles.length > 0 && (
            <div className="text-mut mt-1">
              🏫 Écoles :{' '}
              {ecoles.map((e, i) => (
                <span key={e.nom}>
                  {i > 0 && ' · '}
                  <a href={e.url} target="_blank" rel="noreferrer" className="!text-ink hover:text-accent underline">
                    {e.nom}
                  </a>
                  {e.note ? ` (${e.note})` : ''}
                </span>
              ))}
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
