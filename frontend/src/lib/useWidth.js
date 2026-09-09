import { useEffect, useRef, useState } from 'react'

// Largeur réelle d'un conteneur (ResizeObserver). Les SVG (marée, rose) se dessinent
// en pixels réels plutôt qu'avec un viewBox étiré : les textes restent lisibles à
// 360 px comme à 1200 px (un viewBox réduit à 60 % donnerait des libellés de 6 px).
export function useWidth(initial = 320) {
  const ref = useRef(null)
  const [w, setW] = useState(initial)
  useEffect(() => {
    const el = ref.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(([entry]) => {
      const cw = Math.floor(entry.contentRect.width)
      if (cw > 0) setW(cw)
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  return [ref, w]
}
