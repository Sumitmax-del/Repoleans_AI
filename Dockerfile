# ============================================================================
# Stage 1 — Build the React frontend
# ============================================================================
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend

# Install dependencies first (layer cache)
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy source and build
COPY frontend/ ./
RUN npm run build


# ============================================================================
# Stage 2 — Python runtime
# ============================================================================
FROM python:3.11-slim AS runtime

# System dependencies: git (repo cloning), build-essential (numpy/native wheels)
RUN apt-get update && \
    apt-get install -y --no-install-recommends git build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies — install before copying app code for cache efficiency
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt && \
    pip install --no-cache-dir google-genai

# Copy application code
COPY backend/ ./backend/
COPY README.md ./

# Copy compiled frontend from Stage 1
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Copy .env.example as a reference (actual .env is set via platform env vars)
COPY .env.example ./

EXPOSE 8000

# PORT is injected by most cloud platforms (Render, Railway, Cloud Run);
# falls back to 8000 for local docker run.
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
