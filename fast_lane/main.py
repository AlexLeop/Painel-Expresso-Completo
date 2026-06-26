from fastapi import FastAPI, Header, HTTPException, status, Depends
from pydantic import BaseModel
import redis
import json
import time
from typing import Optional
import os

app = FastAPI(title="NevesGo Fast-Lane Telemetry Gateway")

# Conexão Redis O(1) Isolada (Sem ORM PostgreSQL)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)


class TelemetryPayload(BaseModel):
    lat: float
    lng: float
    heading: Optional[int] = 0
    speedKmh: Optional[int] = 0
    timestamp: int


def verify_device_token(x_device_token: str = Header(...)):
    if not x_device_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Token"
        )

    try:
        # Busca o token no Redis
        from typing import cast
        import json

        driver_data_json = cast(
            str, redis_client.get(f"fastlane:token_meta:{x_device_token}")
        )
        if not driver_data_json:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or Expired Token",
            )

        driver_data = json.loads(driver_data_json)
        driver_id = driver_data.get("driver_id")
        operator_id = driver_data.get("operator_id")

        # O(1) Deny-list Check
        if redis_client.get(f"deny_list:driver:{driver_id}") or redis_client.get(
            f"deny_list:operator:{operator_id}"
        ):
            # Preventivamente limpa o token roubado/bloqueado
            redis_client.delete(f"fastlane:token_meta:{x_device_token}")
            redis_client.zrem("fastlane:driver_tokens", x_device_token)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Blocked by Deny-list"
            )

        return {"driver_id": driver_id, "operator_id": operator_id}

    except redis.exceptions.ConnectionError:
        # Política Fail-Closed: Melhor perder 2 minutos de trilha do que aceitar fraudadores às cegas
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fail-closed. Cache unavailable.",
        )


@app.post("/telemetry")
async def ingest_telemetry(
    payload: TelemetryPayload, driver_info: dict = Depends(verify_device_token)
):
    driver_id = driver_info["driver_id"]
    operator_id = driver_info["operator_id"]

    ts_server = int(time.time())

    try:
        # Pipeline atômico para gravar nos dois locais em 1 RT
        pipeline = redis_client.pipeline()

        # 1. Fast-Path (Live Tracking - Supabase/Dashboard)
        # GEOADD key longitude latitude member
        pipeline.geoadd(
            f"driver_positions:{operator_id}", [payload.lng, payload.lat, driver_id]
        )

        # 2. Slow-Path (Worker Celery a cada 2 min)
        raw_event = json.dumps(
            {
                "driver_id": driver_id,
                "operator_id": operator_id,
                "lat": payload.lat,
                "lng": payload.lng,
                "heading": payload.heading,
                "speed": payload.speedKmh,
                "ts_device": payload.timestamp,
                "ts_server": ts_server,
            }
        )
        pipeline.rpush(f"queue:telemetry_raw_{operator_id}", raw_event)

        # 3. Geofence Auto-Arrive trigger
        # Busca stops cadastrados num raio de 150m da posição atual
        nearby_stops = redis_client.georadius(
            f"driver:location:{operator_id}", payload.lng, payload.lat, 150, unit="m"
        )
        if isinstance(nearby_stops, list):
            for member_obj in nearby_stops:
                member = (
                    member_obj.decode("utf-8")
                    if isinstance(member_obj, bytes)
                    else str(member_obj)
                )
                if member.startswith("stop:"):
                    stop_id = member.split(":")[1]
                    trigger_event = json.dumps(
                        {"driver_id": driver_id, "stop_id": stop_id, "action": "ENTER"}
                    )
                    pipeline.rpush("geofence_triggers", trigger_event)

        pipeline.execute()
        return {"status": "ingested"}

    except redis.exceptions.ConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis connection failed",
        )
