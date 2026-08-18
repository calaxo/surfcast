// Helpers d'affichage partagés.

export const scoreColor = (s) =>
  s >= 8 ? '#37d67a' : s >= 5 ? '#f6c945' : '#ff6b6b'

// mêmes seuils que les labels backend -> couleur = label (plus de "mal orientée" en vert)
export const factorColor = (f) =>
  f >= 0.7 ? '#37d67a' : f >= 0.45 ? '#f6c945' : '#ff6b6b'

// **gras** -> <b> (les explications backend utilisent cette syntaxe)
export const mdBold = (t = '') =>
  t.replace(/\*\*(.+?)\*\*/g, '<b class="text-accent">$1</b>')

export const fmtDate = (isoDay) =>
  new Date(isoDay + 'T12:00').toLocaleDateString('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })

export const fmtDateFull = (isoDay) =>
  new Date(isoDay + 'T12:00').toLocaleDateString('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })

export const driveTxt = (min) => {
  if (min == null) return ''
  const h = Math.floor(min / 60)
  const m = min % 60
  return h ? `${h}h${m ? String(m).padStart(2, '0') : ''}` : `${m} min`
}

// meilleur créneau de jour (7h-21h) d'une liste d'évals pour un jour donné
export function bestOfDay(evals, day) {
  const es = evals.filter((e) => e.time.slice(0, 10) === day)
  const dl = es.filter((e) => {
    const h = +e.time.slice(11, 13)
    return h >= 7 && h <= 21
  })
  const pool = dl.length ? dl : es
  return pool.reduce((a, b) => (b.score > a.score ? b : a), pool[0])
}

export const daysOf = (evals) => [...new Set(evals.map((e) => e.time.slice(0, 10)))]
