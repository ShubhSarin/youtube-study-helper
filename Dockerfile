# ---------------------------------------------------------------------------
# Stage 1: build the React (Vite) frontend
# ---------------------------------------------------------------------------
FROM node:22-slim AS web-builder

WORKDIR /build
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: Python backend serving the built SPA
# ---------------------------------------------------------------------------
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core/ ./core/
COPY api/ ./api/
COPY transcript_extractor.py ./
COPY --from=web-builder /build/dist ./web/dist

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
