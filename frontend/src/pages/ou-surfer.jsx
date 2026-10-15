import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '@/store'
import { getRanking } from '@/api'
import { scoreColor, fmtDate, driveTxt } from '@/lib/format'

export default function OuSurfer() {
  const { level, setSpot, me } = useApp()
  const drive = (key) => me.home?.drive_min?.[key]
  const [rows, setRows] = useState(null)
  const [dayIdx, setDayIdx] = useState(0)
  const navigate = useNavigate()

  useEffect(() => {
    getRanking(level).then(setRows)
  }, [level])

  if (!rows) return <div className="text-mut py-8">Calcul des meilleurs spots…</div>

  const days = rows[0]?.days?.map((d) => d.date) || []
  // classe les spots pour le jour choisi (meilleur score d'abord)
  const ranked = rows
    .map((r) => ({ ...r, day: r.days[dayIdx] }))
    .filter((r) => r.day)
    .sort((a, b) => (b.day.score ?? -1) - (a.day.score ?? -1))

  const open = (key) => {
    setSpot(key)
    navigate('/')
  }

  return (
    <div className="mt-4">
      <h2 className="text-lg font-semibold">Où surfer ?</h2>
      <p className="text-mut text-[13px] mb-1">
        Le meilleur créneau de chaque spot, classé. Choisis le jour
        {me.home ? ' ; à score proche, prends le plus proche (ou Oléron 😉).' : '.'}
      </p>

      <div className="flex gap-2 my-3 flex-wrap">
        {days.map((d, i) => (
          <button
            key={d}
            onClick={() => setDayIdx(i)}
            className={`px-3 py-1.5 rounded-lg text-sm border capitalize ${
              i === dayIdx ? 'border-accent text-ink' : 'border-line text-mut hover:text-ink'
            }`}
          >
            {fmtDate(d)}
          </button>
        ))}
      </div>

      <div className="grid gap-2">
        {ranked.map((r, i) => {
          const col = scoreColor(r.day.score)
          return (
            <button
              key={r.key}
              onClick={() => open(r.key)}
              className="card flex items-center gap-4 text-left hover:border-accent py-3"
            >
              <div className="text-mut text-sm w-5 text-center">{i + 1}</div>
              <div
                className="gauge shrink-0"
                style={{ '--c': col, width: 46, height: 46, fontSize: 15 }}
              >
                <span style={{ width: 34, height: 34 }}>{r.day.score}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-semibold">{r.name}</div>
                <div className="text-mut text-[12px]">
                  {r.region}
                  {drive(r.key) != null && <> · 🚗 {driveTxt(drive(r.key))}</>}
                </div>
              </div>
              <div className="text-right shrink-0">
                <div className="font-semibold" style={{ color: col }}>
                  {r.day.label}
                </div>
                <div className="text-mut text-[12px]">
                  vagues ~{r.day.wave_h} m · meilleur {r.day.best_time}
                </div>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
