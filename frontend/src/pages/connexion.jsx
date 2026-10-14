import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '@/store'
import { login, logout } from '@/api'

// Accès perso (journal de sessions, point de départ). Le site reste entièrement
// utilisable sans compte : cette page ne sert qu'au propriétaire.
export default function Connexion() {
  const { me, refreshMe } = useApp()
  const [key, setKey] = useState('')
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setMsg('')
    try {
      if (await login(key)) {
        setKey('')
        await refreshMe()
        navigate('/sessions')
      } else setMsg('Clé incorrecte.')
    } catch (err) {
      setMsg(err.message || 'Connexion impossible pour le moment.')
    } finally {
      setBusy(false)
    }
  }

  const signOut = async () => {
    await logout()
    await refreshMe()
    navigate('/')
  }

  if (me.owner)
    return (
      <div className="py-10 max-w-sm">
        <p className="text-sm">Connecté à l’espace perso.</p>
        <button className="mt-3 text-sm" onClick={signOut}>Se déconnecter</button>
      </div>
    )

  return (
    <form onSubmit={submit} className="py-10 max-w-sm">
      <h2 className="text-lg font-semibold mb-1">Accès perso</h2>
      <p className="text-mut text-[13px] mb-3">
        Réservé au propriétaire du site. Les prévisions restent accessibles à tous sans compte.
      </p>
      <input
        type="password"
        autoComplete="current-password"
        className="w-full"
        value={key}
        onChange={(e) => setKey(e.target.value)}
        aria-label="Clé d’accès"
        placeholder="Clé d’accès"
      />
      <button type="submit" className="mt-3 text-sm" disabled={busy || !key}>
        Se connecter
      </button>
      {msg && <p className="text-sunset text-[13px] mt-2">{msg}</p>}
    </form>
  )
}
