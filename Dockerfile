# Surfcast — image unique : front React buildé + backend Python servis sur un seul port.
# Multi-stage : node build le front, puis runtime python léger.

# --- Stage 1 : build du front (Vite + PWA) ---
FROM node:22-alpine AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build          # -> /fe/dist (SPA + service worker + manifest)

# --- Stage 2 : runtime python ---
FROM python:3.13-slim AS runtime
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1 SURFCAST_STATIC=/app/static

# PyYAML requis (spots.yaml a des structures imbriquées, le mini-parseur ne suffit plus)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# code + données backend
COPY app/ ./app/
COPY server.py spots.yaml sessions.example.json ./
# Le journal de sessions PERSONNEL n'est pas dans l'image : le monter en volume et
# pointer SURFCAST_SESSIONS dessus, par ex.
#   -v ./sessions.json:/data/sessions.json:ro -e SURFCAST_SESSIONS=/data/sessions.json
# Sans ça, l'appli tourne avec l'exemple anonymisé sessions.example.json.
# Accès propriétaire (journal, point de départ) : -e SURFCAST_OWNER_KEY=... (sinon fermé).
# front buildé
COPY --from=frontend /fe/dist ./static

# cache des réponses Open-Meteo (persisté via volume en compose)
RUN mkdir -p /app/cache
VOLUME ["/app/cache"]

EXPOSE 8090
CMD ["python", "server.py", "--port", "8090"]
