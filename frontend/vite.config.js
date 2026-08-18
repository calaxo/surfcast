import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import Pages from 'vite-plugin-pages'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'node:path'

// Front Surfcast : React + Tailwind + Vite.
// - vite-plugin-pages : routing basé sur les fichiers de src/pages
// - vite-plugin-pwa  : app installable + OFFLINE (pas de réseau sur la plage !)
// - alias '@' -> src
// - proxy /api -> backend Python (server.py) pour éviter tout souci CORS en dev
export default defineConfig({
  plugins: [
    react(),
    Pages({ dirs: 'src/pages', extensions: ['jsx'] }),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.png', 'apple-touch-icon.png'],
      manifest: {
        name: 'Surfcast — prévisions surf expliquées',
        short_name: 'Surfcast',
        description: 'Prévisions de surf qui expliquent POURQUOI, avec marée, vent, lumière. Marche hors-ligne.',
        theme_color: '#0b1622',
        background_color: '#0b1622',
        display: 'standalone',
        orientation: 'portrait',
        lang: 'fr',
        start_url: '/',
        icons: [
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: 'maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,png,svg,woff2}'],   // app-shell précachée → charge hors-ligne
        navigateFallback: '/index.html',
        runtimeCaching: [
          {
            // Les /api : NETWORK-FIRST → on tente le réseau (5G aléatoire, voiture),
            // et à défaut on sert la DERNIÈRE prévision connue (backup hors-ligne).
            urlPattern: ({ url }) => url.pathname.startsWith('/api/'),
            handler: 'NetworkFirst',
            options: {
              cacheName: 'surfcast-api',
              networkTimeoutSeconds: 4,        // pas de réseau en 4 s → on bascule sur le cache
              expiration: { maxEntries: 60, maxAgeSeconds: 60 * 60 * 24 * 3 },  // garde 3 j
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
      devOptions: { enabled: true },   // PWA active aussi en dev (npm run dev)
    }),
  ],
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8090', changeOrigin: true },
    },
  },
})
