# ── Étape 1 : Build & Dépendances ──────────────────────────────
FROM python:3.10-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Étape 2 : Image d'Exécution Minimale (Production) ──────────
FROM python:3.10-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0

# Copie des bibliothèques Python depuis le builder
COPY --from=builder /install /usr/local

# Création d'un utilisateur non-root pour la sécurité en production
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/notebooks/artifacts /app/artifacts && \
    chown -R appuser:appuser /app

# Copie des configurations et du code source
COPY --chown=appuser:appuser pyproject.toml .
COPY --chown=appuser:appuser main.py .
COPY --chown=appuser:appuser order.json .
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser notebooks/artifacts/ ./notebooks/artifacts/
COPY --chown=appuser:appuser artifacts/ ./artifacts/

# Installation du package livraison-express-lite en mode local
RUN pip install --no-cache-dir -e .

USER appuser

EXPOSE 8000

# Sonde de santé intégrée au conteneur Docker
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Point d'entrée de production
CMD ["python", "main.py", "serve", "--host", "0.0.0.0", "--port", "8000"]
