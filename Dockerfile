FROM python:3.14-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SCHEMA_MIGRATIONS_DIR=/app/database/migrations

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY backend/ /app/
COPY database/migrations/ /app/database/migrations/

RUN useradd --create-home --uid 10001 appuser && \
    mkdir -p /app/static /app/media && \
    chown -R appuser:appuser /app

EXPOSE 8000
USER appuser

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "config.wsgi:application"]
