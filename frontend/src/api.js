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

// --- Partie personnelle (propriétaire) ---------------------------------------
// /api/me répond toujours 200 : {owner:false} pour un visiteur. Jamais d'erreur visible :
// au moindre souci (hors-ligne, serveur ancien), on se considère simplement visiteur.
export async function getMe() {
  try {
    const r = await fetch('/api/me', { cache: 'no-store', credentials: 'same-origin' })
    return r.ok ? await r.json() : { owner: false }
  } catch {
    return { owner: false }
  }
}

export async function login(key) {
  const r = await fetch('/api/login', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key }),
  })
  if (r.ok) return true
  if (r.status === 429) throw new Error('Trop d’essais, patiente une minute.')
  return false
}

export const logout = () =>
  fetch('/api/logout', { method: 'POST', credentials: 'same-origin' }).catch(() => {})
export const getForecast = (spot, model = '', level = 'debutant') =>
  getJSON(`/api/forecast?spot=${encodeURIComponent(spot)}&model=${encodeURIComponent(model)}&level=${level}`)
// Jamais mis en cache (ni HTTP, ni service worker) : données personnelles.
export async function getSessions(model = '') {
  const r = await fetch(`/api/sessions?model=${encodeURIComponent(model)}`, {
    cache: 'no-store',
    credentials: 'same-origin',
  })
  if (!r.ok) throw new Error(`sessions -> ${r.status}`)
  return r.json()
}
export const getOverview = (model = '', level = 'debutant') =>
  getJSON(`/api/overview?model=${encodeURIComponent(model)}&level=${level}`)
export const getRanking = (level = 'debutant') =>
  getJSON(`/api/ranking?level=${level}`)
export const getBuoy = (spot) => getJSON(`/api/buoy?spot=${encodeURIComponent(spot)}`)
