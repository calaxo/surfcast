import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MapContainer, TileLayer, CircleMarker, Marker, Popup, Tooltip, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useApp } from '@/store'
import { getOverview } from '@/api'
import { scoreColor, driveTxt } from '@/lib/format'

// Icône "maison" (point de départ) en pur DivIcon -> pas de souci d'assets Leaflet.
const homeIcon = L.divIcon({
  className: '',
  html: '<div style="font-size:22px;line-height:22px">🏠</div>',
  iconSize: [22, 22],
  iconAnchor: [11, 11],
})

// Cadre automatiquement la carte sur l'ensemble des points (spots + domicile).
function FitBounds({ points }) {
  const map = useMap()
  useEffect(() => {
    if (points.length < 1) return
    const bounds = L.latLngBounds(points)
    map.fitBounds(bounds, { padding: [40, 40] })
  }, [points, map])
  return null
}

export default function Carte() {
  const { config, model, level, setSpot } = useApp()
  const [spots, setSpots] = useState([])
  const navigate = useNavigate()
  const home = config?.home

  useEffect(() => {
    getOverview(model, level).then(setSpots)
  }, [model, level])

  const openSpot = (key) => {
    setSpot(key)
    navigate('/')
  }

  return (
    <div className="mt-4">
      <h2 className="text-lg font-semibold mb-1">Carte des spots</h2>
      <p className="text-mut text-[13px] mb-3">
        Score du jour par spot (couleur), distance de route depuis le point de départ. Clique un
        spot pour voir sa prévision détaillée.
      </p>

      <div className="card p-0 overflow-hidden">
        <MapContainer
          center={[45.75, -0.55]}
          zoom={8}
          scrollWheelZoom={false}
          style={{ height: 460, width: '100%' }}
        >
          <TileLayer
            attribution='&copy; OpenStreetMap'
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          <FitBounds
            points={[
              ...(home ? [[home.latitude, home.longitude]] : []),
              ...spots.map((s) => [s.lat, s.lon]),
            ]}
          />

          {home && (
            <Marker position={[home.latitude, home.longitude]} icon={homeIcon}>
              <Tooltip>{home.name} (départ)</Tooltip>
            </Marker>
          )}

          {spots.map((s) => {
            const col = s.today_score == null ? '#8aa4bd' : scoreColor(s.today_score)
            return (
              <CircleMarker
                key={s.key}
                center={[s.lat, s.lon]}
                radius={11}
                pathOptions={{ color: col, fillColor: col, fillOpacity: 0.75, weight: 2 }}
                eventHandlers={{ click: () => openSpot(s.key) }}
              >
                <Tooltip>
                  {s.name} — {s.today_score ?? '—'}/10
                </Tooltip>
                <Popup>
                  <div style={{ minWidth: 180 }}>
                    <div style={{ fontWeight: 700 }}>{s.name}</div>
                    <div style={{ color: '#555', fontSize: 12 }}>{s.region}</div>
                    <div style={{ margin: '6px 0' }}>
                      Aujourd'hui :{' '}
                      <b style={{ color: col }}>{s.today_score ?? '—'}/10</b>{' '}
                      {s.today_label ? `(${s.today_label})` : ''}
                      {s.best_time ? ` · ${s.best_time}` : ''}
                    </div>
                    <div style={{ fontSize: 12, color: '#555' }}>
                      🚗 {driveTxt(s.drive_min)} depuis le point de départ · niveau {s.level}
                    </div>
                    <button
                      onClick={() => openSpot(s.key)}
                      style={{
                        marginTop: 8,
                        background: '#38bdf8',
                        color: '#08131f',
                        border: 0,
                        borderRadius: 6,
                        padding: '5px 10px',
                        fontWeight: 600,
                        cursor: 'pointer',
                      }}
                    >
                      Voir la prévision →
                    </button>
                  </div>
                </Popup>
              </CircleMarker>
            )
          })}
        </MapContainer>
      </div>

      <div className="grid gap-2.5 mt-3 [grid-template-columns:repeat(auto-fit,minmax(190px,1fr))]">
        {spots
          .slice()
          .sort((a, b) => (b.today_score ?? -1) - (a.today_score ?? -1))
          .map((s) => (
            <button
              key={s.key}
              onClick={() => openSpot(s.key)}
              className="card text-left hover:border-accent"
            >
              <div className="flex justify-between items-center">
                <span className="font-semibold">{s.name}</span>
                <span
                  className="chip"
                  style={{
                    background: (s.today_score == null ? '#8aa4bd' : scoreColor(s.today_score)) + '22',
                    color: s.today_score == null ? '#8aa4bd' : scoreColor(s.today_score),
                  }}
                >
                  {s.today_score ?? '—'}/10
                </span>
              </div>
              <div className="text-mut text-[12px] mt-1">
                {s.region} · 🚗 {driveTxt(s.drive_min)} · {s.level}
              </div>
            </button>
          ))}
      </div>
    </div>
  )
}
