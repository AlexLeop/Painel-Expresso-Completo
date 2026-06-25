import os
import json
import time
import asyncio
import logging
from typing import Optional
from fastapi import FastAPI, Header, HTTPException, Request, Depends
from pydantic import BaseModel, Field
import redis.asyncio as redis
from redis import exceptions as redis_exceptions

import httpx

# --- Logging Setup ---
logger = logging.getLogger(__name__)

# --- App Initialization ---
app = FastAPI(
    title="Expresso Neves - Fast Lane",
    description="Microserviço de ingestão de telemetria de altíssima performance para motoboys.",
    version="1.0.0"
)

# --- Supabase Realtime Config ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "http://localhost:54321")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "anon-or-service-key")
http_client = httpx.AsyncClient()

# --- Redis Connection ---
# Utilizamos o driver assíncrono para garantir não bloqueio no event loop do FastAPI.
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/1")
redis_pool = redis.ConnectionPool.from_url(REDIS_URL, decode_responses=True)
r = redis.Redis(connection_pool=redis_pool)

# --- Pydantic Schemas ---
import sys
from pathlib import Path
# Add project root to sys.path to allow importing shared_schemas
sys.path.append(str(Path(__file__).resolve().parent.parent))
from shared_schemas.logistics import TelemetryPayload

# --- Security Dependencies ---
async def verify_device_token(x_device_token: str = Header(...)):
    """
    Injeção de Dependência que valida a AUTENTICIDADE do token no Redis.
    O Token não é só uma chave na Denylist, ele é a chave primária da Sessão na Fast Lane!
    """
    if not x_device_token:
        raise HTTPException(status_code=401, detail="Device token missing")
        
    try:
        # Checa e extrai a identidade validada do Motorista.
        token_meta_raw = await r.get(f"fastlane:token_meta:{x_device_token}")
        if not token_meta_raw:
            raise HTTPException(status_code=401, detail="Invalid or expired device token")
            
        token_meta = json.loads(token_meta_raw)
        driver_id = token_meta["driver_id"]
        
        # Barreira 1 (Contrato 4.2): Deny-list de Driver com Kill Switch
        is_driver_banned = await r.get(f"deny_list:driver:{driver_id}")
        if is_driver_banned:
            # 1. Deleta o Device Token preventivamente (impede reconexão)
            await r.delete(f"fastlane:token_meta:{x_device_token}")
            await r.zrem(f"fastlane:driver_tokens:{driver_id}", x_device_token)
            # 2. Retorna 401 forçando o app a destruir a sessão local
            raise HTTPException(status_code=401, detail="Driver blocked. Session destroyed.")
        
        # Checa se a Transportadora do Motorista foi suspensa por inadimplência
        operator_id = token_meta["operator_id"]
        is_operator_banned = await r.get(f"deny_list:operator:{operator_id}")
        if is_operator_banned:
            raise HTTPException(status_code=403, detail="Operator account is suspended.")
            
        return token_meta
        
    except (redis_exceptions.ConnectionError, redis_exceptions.TimeoutError):
        raise HTTPException(status_code=503, detail="Security Cache Down")

# --- Endpoints ---
@app.post("/telemetry", status_code=202)
async def ingest_telemetry(payload: TelemetryPayload, session_meta: dict = Depends(verify_device_token)):
    """
    Ponto de Entrada da Fast Lane com Segurança Estrita.
    """
    # Identidade Inviolável extraída do Token verificado pelo backend.
    driver_id = session_meta["driver_id"]
    operator_id = session_meta["operator_id"]
    
    ts_server = int(time.time())
    ts_device = payload.timestamp  # Apenas para métricas de latência, NUNCA para particionamento
    
    # Estrutura 1: GEOADD - Chave: driver:location:{operator_id}
    geo_key = f"driver:location:{operator_id}"
    
    await r.geoadd(geo_key, [payload.lng, payload.lat, driver_id])
    
    # Estrutura 2: HSET - Chave: driver:meta:{driver_id}
    meta_key = f"driver:meta:{driver_id}"
    await r.hset(meta_key, mapping={
        "speed": payload.speedKmh,
        "heading": payload.heading,
        "last_ping": ts_server
    })

    # Estrutura 3: RPUSH - Chave: queue:telemetry_raw_{operator_id}
    queue_key = f"queue:telemetry_raw_{operator_id}"
    raw_event = {
        "driver_id": driver_id,
        "operator_id": operator_id,
        "lat": payload.lat,
        "lng": payload.lng,
        "heading": payload.heading,
        "speed": payload.speedKmh,
        "ts_server": ts_server,
        "ts_device": ts_device
    }
    try:
        await r.rpush(queue_key, json.dumps(raw_event))
    except (redis_exceptions.ConnectionError, redis_exceptions.TimeoutError):
        raise HTTPException(status_code=503, detail="Telemetry Queue Unavailable")

    # --- Geofence Engine (Two-Lane Event Driven) ---
    try:
        active_stops = await r.smembers(f"active_stops:driver:{driver_id}")
        for stop_id in active_stops:
            # GEODIST requires both members in the same key
            dist = await r.geodist(geo_key, driver_id, f"stop:{stop_id}:point", unit="m")
            if dist is not None:
                radius = await r.get(f"stop:{stop_id}:radius")
                radius = float(radius) if radius else 150.0
                if dist <= radius:
                    trigger_payload = {
                        "driver_id": driver_id, 
                        "stop_id": stop_id,
                    }
                    await r.rpush("geofence_triggers", json.dumps(trigger_payload))
    except Exception as e:
        logger.error(f"Geofence error: {e}")

    # --- SUPABASE BROADCAST (Radar do Next.js & Public Tracker) ---
    async def broadcast_location():
        try:
            url = f"{SUPABASE_URL}/realtime/v1/api/broadcast"
            headers = {"apikey": SUPABASE_SERVICE_KEY, "Content-Type": "application/json"}
            
            # Broadcast operator tracker
            body_operator = {
                "messages": [{
                    "topic": f"realtime:telemetry_operator_{operator_id}",
                    "event": "location_update",
                    "payload": raw_event
                }]
            }
            await http_client.post(url, headers=headers, json=body_operator)
            
            # Broadcast public tracker
            active_orders = await r.smembers(f"active_orders:driver:{driver_id}")
            for order_id in active_orders:
                is_active = await r.exists(f"public_tracker:{order_id}:active")
                if is_active:
                    body_public = {
                        "messages": [{
                            "topic": f"realtime:public_order_{order_id}",
                            "event": "location_update",
                            "payload": {"lat": payload.lat, "lon": payload.lng}
                        }]
                    }
                    await http_client.post(url, headers=headers, json=body_public)
        except Exception as e:
            logger.error(f"Erro no broadcast de localização: {e}")

    # LOW-001: Adicionar callback para capturar exceções da tarefa assíncrona
    task = asyncio.create_task(broadcast_location())
    def task_done_callback(t):
        try:
            t.result()
        except Exception as e:
            logger.error(f"Tarefa de broadcast falhou: {e}")
    task.add_done_callback(task_done_callback)

    return {"status": "accepted"}

@app.get("/health")
async def health_check():
    """Liveness probe para o Kubernetes / Easypanel."""
    return {"status": "ok", "service": "fast_lane"}
