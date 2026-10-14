import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from '@/App'
import { AppProvider } from '@/store'
import '@/index.css'

// L'ancien cache du service worker (« surfcast-api ») pouvait contenir /api/sessions :
// on le supprime. Les nouvelles versions n'y mettent plus rien de personnel.
if ('caches' in window) caches.delete('surfcast-api').catch(() => {})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AppProvider>
        <App />
      </AppProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
