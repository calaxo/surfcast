import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useApp, NIVEAUX } from '@/store'
import { getLastSync } from '@/api'

const tabs = [
  { to: '/', label: 'Prévisions', end: true },
  { to: '/ou-surfer', label: 'Où surfer ?' },
  { to: '/carte', label: 'Carte' },
  { to: '/sessions', label: 'Sessions' },
  { to: '/science', label: 'La science' },
]

function OfflineBadge() {
  const [online, setOnline] = useState(navigator.onLine)
  useEffect(() => {
    const on = () => setOnline(true)
    const off = () => setOnline(false)
    window.addEventListener('online', on)
    window.addEventListener('offline', off)
    return () => {
      window.removeEventListener('online', on)
      window.removeEventListener('offline', off)
    }
  }, [])
  if (online) return null
  const last = getLastSync()
  const txt = last
    ? `données du ${new Date(last).toLocaleString('fr-FR', { weekday: 'short', hour: '2-digit', minute: '2-digit' })}`
    : 'aucune donnée en cache'
  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-amber-500/15 text-amber-300 text-xs border border-amber-500/30">
      ⚡ Hors-ligne · {txt}
    </span>
  )
}

export default function Header() {
  const { config, spot, setSpot, level, setLevel } = useApp()
  const spots = config?.spots || {}

  return (
    <header className="max-w-5xl mx-auto px-4 pt-6">
      <div className="flex items-center justify-between gap-2">
        <h1 className="text-2xl font-bold m-0">🌊 Surfcast</h1>
        <OfflineBadge />
      </div>
      <p className="text-mut text-[13px] mt-1">
        Pas juste un score : <b className="text-accent">pourquoi</b> les vagues sont
        comme ça. Spots accessibles en journée depuis le point de départ.
      </p>

      <div className="flex gap-3 items-center flex-wrap my-3">
        <label className="text-sm">
          Spot{' '}
          <select
            className="bg-card text-ink border border-line rounded-lg px-2.5 py-1.5 text-sm"
            value={spot || ''}
            onChange={(e) => setSpot(e.target.value)}
          >
            {Object.entries(spots).map(([k, v]) => (
              <option key={k} value={k}>
                {v.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Niveau{' '}
          <select
            className="bg-card text-ink border border-line rounded-lg px-2.5 py-1.5 text-sm"
            value={level}
            onChange={(e) => setLevel(e.target.value)}
          >
            {NIVEAUX.map((n) => (
              <option key={n.value} value={n.value}>
                {n.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <nav className="flex gap-1.5 border-b border-line">
        {tabs.map((t) => (
          <NavLink
            key={t.to}
            to={t.to}
            end={t.end}
            className={({ isActive }) =>
              `px-3.5 py-2.5 text-sm border-b-2 -mb-px ${
                isActive
                  ? 'text-ink border-accent'
                  : 'text-mut border-transparent hover:text-ink'
              }`
            }
          >
            {t.label}
          </NavLink>
        ))}
      </nav>
    </header>
  )
}
