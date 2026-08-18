import { createContext, useContext, useEffect, useState } from 'react'
import { getConfig } from '@/api'

// État global léger : config des spots + sélection courante (spot, modèle),
// partagée entre les pages Prévisions / Sessions / Carte.
const Ctx = createContext(null)

export function AppProvider({ children }) {
  const [config, setConfig] = useState(null)
  const [spot, setSpot] = useState(null)
  const [model, setModel] = useState('')
  const [level, setLevel] = useState('debutant')

  useEffect(() => {
    getConfig().then((cfg) => {
      setConfig(cfg)
      const first = Object.keys(cfg.spots || {})[0]
      setSpot((s) => s || first)
    })
  }, [])

  return (
    <Ctx.Provider value={{ config, spot, setSpot, model, setModel, level, setLevel }}>
      {children}
    </Ctx.Provider>
  )
}

export const useApp = () => useContext(Ctx)

export const MODELS = [
  { value: '', label: 'Auto (Open-Meteo)' },
  { value: 'meteofrance_wave', label: 'Météo-France (MFWAM)' },
  { value: 'gwam', label: 'GWAM (DWD)' },
  { value: 'ewam', label: 'EWAM (Europe fin)' },
]

export const NIVEAUX = [
  { value: 'debutant', label: 'Débutant' },
  { value: 'intermediaire', label: 'Intermédiaire' },
  { value: 'confirme', label: 'Confirmé' },
]
