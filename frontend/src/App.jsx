import { Suspense } from 'react'
import { Link, useRoutes } from 'react-router-dom'
import routes from '~react-pages'
import Header from '@/components/Header'
import { useApp } from '@/store'

export default function App() {
  const element = useRoutes(routes)
  const { me } = useApp()
  return (
    <div className="min-h-screen">
      <Header />
      <main className="max-w-5xl mx-auto px-4 pb-16">
        <Suspense fallback={<div className="text-mut py-8">Chargement…</div>}>
          {element}
        </Suspense>
      </main>
      <footer className="max-w-5xl mx-auto px-4 pb-12 text-mut text-xs">
        Note = <b>surfabilité pour ton niveau</b> : taille de vague adaptée (en cloche, pas
        "le plus gros = mieux") × propreté (période) × vent × orientation. Tout est explicite
        dans <code>app/science.py</code>. Données : Open-Meteo (MFWAM/GWAM/EWAM) + archive.
        <Link to="/connexion" className="block mt-3 text-mut/60 hover:text-mut no-underline">
          {me.owner ? 'Espace perso · déconnexion' : 'Accès perso'}
        </Link>
      </footer>
    </div>
  )
}
