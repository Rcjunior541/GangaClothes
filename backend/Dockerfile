# ==============================================================================
# GangaClothes API - Multi-stage Production Dockerfile
# ==============================================================================

# --- Etapa 1: Builder (Instalación de dependencias en venv aislado) ---
FROM python:3.12-slim-bookworm AS builder

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

RUN python -m venv "${VIRTUAL_ENV}"

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# --- Etapa 2: Runtime (Imagen final liviana y segura) ---
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    PORT=8000

WORKDIR /app

# Crear usuario sin privilegios root y asegurar permisos en /app
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home app \
    && chown -R app:app /app

# Copiar entorno virtual compilado
COPY --from=builder /opt/venv /opt/venv

# Copiar código de la aplicación, módulos y scripts de inicialización / seed
COPY --chown=app:app app ./app
COPY --chown=app:app seed.py seed_demo.py ./

USER app

EXPOSE 8000

# Al arrancar: corre migraciones y el seeder (idempotente, crea tablas/datos si faltan)
# y luego levanta uvicorn escuchando en el puerto configurado (ej. Render PORT o 8000).
CMD ["sh", "-c", "python seed.py && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
