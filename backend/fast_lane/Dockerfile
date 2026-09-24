FROM python:3.14-slim-bookworm

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copia tudo para permitir a leitura do shared_schemas
COPY . /app/

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app

WORKDIR /app/fast_lane

EXPOSE 8001
USER appuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4"]
