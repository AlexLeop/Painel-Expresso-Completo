# Root Dockerfile for EasyPanel (Django, Celery Worker, Celery Beat)
FROM python:3.14-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY backend/ /app/

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "config.wsgi:application"]
