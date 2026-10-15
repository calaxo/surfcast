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
// /api/me répond toujours 200 : {owner:false} pour un visiteur. Le service worker ne le
// met jamais en cache ; c'est l'appli qui garde la dernière réponse PROPRIÉTAIRE dans le
// localStorage de l'appareil, pour rester propriétaire hors-ligne (plage, voiture).
// Le serveur garde le dernier mot : dès qu'il répond {owner:false}, on oublie tout.
const ME = 'surfcast:me'
const SESS = 'surfcast:sessions'

const readLocal = (k) => {
  try {
    return JSON.parse(localStorage.getItem(k))
  } catch {
    return null
  }
}
const writeLocal = (k, v) => {
  try {
    localStorage.setItem(k, JSON.stringify(v))
  } catch {}
}
export function forgetOwner() {
  try {
    localStorage.removeItem(ME)
    Object.keys(localStorage)
      .filter((k) => k.startsWith(SESS))
      .forEach((k) => localStorage.removeItem(k))
  } catch {}
}

export async function getMe() {
  let r
  try {
    r = await fetch('/api/me', { cache: 'no-store', credentials: 'same-origin' })
  } catch {
    // pas de réseau : dernière réponse propriétaire connue sur cet appareil
    const saved = readLocal(ME)
    return saved?.owner ? { ...saved, offline: true } : { owner: false }
  }
  if (!r.ok) return { owner: false }
  const me = await r.json()
  if (me.owner) writeLocal(ME, me)
  else forgetOwner()
  return me
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

export const logout = () => {
  forgetOwner()
  return fetch('/api/logout', { method: 'POST', credentials: 'same-origin' }).catch(() => {})
}
export const getForecast = (spot, model = '', level = 'debutant') =>
  getJSON(`/api/forecast?spot=${encodeURIComponent(spot)}&model=${encodeURIComponent(model)}&level=${level}`)
// Jamais mis en cache HTTP ni service worker : données personnelles. La dernière réponse
// est gardée dans le localStorage de l'appareil (effacée à la déconnexion) pour pouvoir
// relire son journal hors-ligne.
export async function getSessions(model = '') {
  const key = `${SESS}:${model}`
  let r
  try {
    r = await fetch(`/api/sessions?model=${encodeURIComponent(model)}`, {
      cache: 'no-store',
      credentials: 'same-origin',
    })
  } catch (err) {
    const saved = readLocal(key)
    if (saved) return saved
    throw err
  }
  if (!r.ok) throw new Error(`sessions -> ${r.status}`)
  const data = await r.json()
  writeLocal(key, data)
  return data
}
export const getOverview = (model = '', level = 'debutant') =>
  getJSON(`/api/overview?model=${encodeURIComponent(model)}&level=${level}`)
export const getRanking = (level = 'debutant') =>
  getJSON(`/api/ranking?level=${level}`)
export const getBuoy = (spot) => getJSON(`/api/buoy?spot=${encodeURIComponent(spot)}`)
