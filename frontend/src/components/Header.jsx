import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useApp, NIVEAUX } from '@/store'
import { getLastSync } from '@/api'

const tabs = [
  { to: '/', label: 'Prévisions', end: true },
  { to: '/ou-surfer', label: 'Où surfer ?' },
  { to: '/carte', label: 'Carte' },
  { to: '/sessions', label: 'Sessions', owner: true },   // perso : propriétaire seulement
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
    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-sunset/15 text-sunset text-[11px] font-medium border border-sunset/30 whitespace-nowrap">
      ⚡ Hors-ligne · {txt}
    </span>
  )
}

export default function Header() {
  const { config, spot, setSpot, level, setLevel, me } = useApp()
  const spots = config?.spots || {}

  return (
    <header className="sticky top-0 z-20 bg-bg/85 backdrop-blur-md border-b border-line">
      <div className="max-w-5xl mx-auto px-4 pt-3">
        {/* marque + statut hors-ligne */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-xl leading-none" aria-hidden>🌊</span>
            <h1 className="text-lg font-bold m-0 tracking-tight">Surfcast</h1>
            <span className="hidden sm:inline text-mut text-[12px] truncate">
              — pourquoi les vagues sont comme ça
            </span>
          </div>
          <OfflineBadge />
        </div>

        {/* contrôles : spot + niveau */}
        <div className="flex gap-2 mt-2.5">
          <select
            className="flex-1 min-w-0"
            value={spot || ''}
            onChange={(e) => setSpot(e.target.value)}
            aria-label="Spot"
          >
            {Object.entries(spots).map(([k, v]) => (
              <option key={k} value={k}>{v.name}</option>
            ))}
          </select>
          <select
            className="shrink-0"
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            aria-label="Niveau"
          >
            {NIVEAUX.map((n) => (
              <option key={n.value} value={n.value}>{n.label}</option>
            ))}
          </select>
        </div>

        {/* onglets : scroll horizontal propre sur mobile (fini le débordement) */}
        <nav className="flex gap-1 mt-2 overflow-x-auto no-scrollbar -mx-4 px-4">
          {tabs.filter((t) => !t.owner || me.owner).map((t) => (
            <NavLink
              key={t.to}
              to={t.to}
              end={t.end}
              className={({ isActive }) =>
                `shrink-0 whitespace-nowrap px-3 py-2.5 text-sm border-b-2 -mb-px transition-colors ${
                  isActive
                    ? 'text-ink border-accent font-medium'
                    : 'text-mut border-transparent hover:text-ink'
                }`
              }
            >
              {t.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  )
}
