// Accès au backend Python (proxy Vite /api -> http://localhost:8090).
// En PWA installée, le service worker sert les /api en NetworkFirst : quand il n'y
// a pas de réseau (plage, 5G aléatoire, voiture), on récupère la DERNIÈRE prévision
// mise en cache. On note l'heure de la dernière vraie synchro pour l'afficher.
const LAST_SYNC = 'surfcast:lastSync'

async function getJSON(url) {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${url} -> ${r.status}`)
  const data = await r.json()
  if (navigator.onLine) localStorage.setItem(LAST_SYNC, new Date().toISOString())
  return data
}

export const getLastSync = () => localStorage.getItem(LAST_SYNC)
export const isOnline = () => navigator.onLine

export const getConfig = () => getJSON('/api/config')
export const getForecast = (spot, model = '', level = 'debutant') =>
  getJSON(`/api/forecast?spot=${encodeURIComponent(spot)}&model=${encodeURIComponent(model)}&level=${level}`)
export const getSessions = (model = '') =>
  getJSON(`/api/sessions?model=${encodeURIComponent(model)}`)
export const getOverview = (model = '', level = 'debutant') =>
  getJSON(`/api/overview?model=${encodeURIComponent(model)}&level=${level}`)
export const getRanking = (level = 'debutant') =>
  getJSON(`/api/ranking?level=${level}`)
