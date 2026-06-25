import json
import time
import threading
from functools import wraps
from django.http import JsonResponse, HttpResponse
import redis
import os


def _env_flag(*names: str) -> bool:
    for name in names:
        value = os.environ.get(name, "").strip().lower()
        if value in {"1", "true", "yes", "on"}:
            return True
    return False


REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/1")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
ALLOW_MEMORY_FALLBACK = _env_flag("IDEMPOTENCY_ALLOW_MEMORY_FALLBACK", "REDIS_ALLOW_MEMORY_FALLBACK")
_MEM_LOCKS: dict[str, threading.Lock] = {}
_MEM_RESPONSES: dict[str, tuple[float, dict]] = {}

def _mem_get(key: str):
    item = _MEM_RESPONSES.get(key)
    if not item:
        return None
    expires_at, payload = item
    if expires_at < time.time():
        _MEM_RESPONSES.pop(key, None)
        return None
    return payload

def _mem_set(key: str, payload: dict, timeout: int):
    _MEM_RESPONSES[key] = (time.time() + int(timeout), payload)

def _mem_acquire(lock_key: str) -> bool:
    lock = _MEM_LOCKS.get(lock_key)
    if lock is None:
        lock = threading.Lock()
        _MEM_LOCKS[lock_key] = lock
    return lock.acquire(blocking=False)

def _mem_release(lock_key: str):
    lock = _MEM_LOCKS.get(lock_key)
    if lock and lock.locked():
        lock.release()

def _try_schema_dump(schema, response):
    try:
        if isinstance(response, list):
            return [schema.model_validate(obj).model_dump(mode='json') for obj in response]
        return schema.model_validate(response).model_dump(mode='json')
    except Exception:
        return None

def idempotent(timeout=86400, schema=None):
    """
    Decorador para endpoints mutáveis (POST, PUT, PATCH).
    Exige cabeçalho 'Idempotency-Key' no Request.
    Faz lock no Redis para evitar concorrência e faz cache da resposta para retry seguro.
    Se 'schema' for passado (ex: schema=OrderSchema), o objeto retornado (ex: model do Django ORM)
    será serializado pelo schema antes de ser salvo no Redis, evitando TypeError do json.dumps.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.method not in ['POST', 'PUT', 'PATCH']:
                return view_func(request, *args, **kwargs)

            idem_key = request.headers.get('Idempotency-Key')
            if not idem_key:
                return JsonResponse({"error": "Idempotency-Key header is required"}, status=400)
            
            user_id = request.auth.get('sub', 'anonymous') if hasattr(request, 'auth') and request.auth else 'anonymous'
            path = request.path
            
            # Escopo estrito para evitar colisões globais maliciosas ou acidentais
            redis_lock_key = f"idempotency:lock:{user_id}:{path}:{idem_key}"
            redis_response_key = f"idempotency:response:{user_id}:{path}:{idem_key}"
            
            # Se já respondeu antes, retorna o cache garantindo a Idempotência real
            try:
                cached_response = r.get(redis_response_key)
                if cached_response:
                    data = json.loads(cached_response)
                    return JsonResponse(data.get('data'), status=data.get('status'))
            except Exception:
                if ALLOW_MEMORY_FALLBACK:
                    cached = _mem_get(redis_response_key)
                    if cached:
                        return JsonResponse(cached.get('data'), status=cached.get('status'))

            # Tenta pegar o Lock (impede duplo-clique simultâneo)
            mem_lock_acquired = False
            try:
                # SET NX EX atômico: impede deadlock se o processo morrer entre lock e expire
                acquired = r.set(redis_lock_key, "PROCESSING", nx=True, ex=60)
                if not acquired:
                    return JsonResponse(
                        {"message": "Requisição duplicada e em processamento."},
                        status=409
                    )
            except Exception:
                if not ALLOW_MEMORY_FALLBACK:
                    return JsonResponse({"error": "Failed to acquire lock"}, status=503)
                mem_lock_acquired = _mem_acquire(redis_lock_key)
                if not mem_lock_acquired:
                    return JsonResponse({"message": "Requisição duplicada e em processamento."}, status=409)

            try:
                # Executa a view original
                response = view_func(request, *args, **kwargs)
                
                # Prepara o cache da resposta
                if isinstance(response, HttpResponse):
                    status_code = response.status_code
                    try:
                        content = json.loads(response.content)
                    except:
                        content = response.content.decode('utf-8')
                elif isinstance(response, tuple):
                    status_code = response[0]
                    content = response[1]
                else:
                    status_code = 200
                    content = response
                    
                # Serialização explícita do ORM se um schema for provido (Ninja-agnóstico)
                if schema and not isinstance(response, HttpResponse):
                    dumped = _try_schema_dump(schema, response)
                    if dumped is not None:
                        content = dumped
                elif hasattr(content, 'dict'):
                    content = content.dict()
                
                if 200 <= status_code < 300:
                    response_data = {
                        "status": status_code,
                        "data": content
                    }
                    try:
                        r.set(redis_response_key, json.dumps(response_data), ex=timeout)
                    except Exception:
                        if ALLOW_MEMORY_FALLBACK:
                            _mem_set(redis_response_key, response_data, timeout)
                        
                return response
            finally:
                try:
                    r.delete(redis_lock_key)
                except Exception:
                    if mem_lock_acquired:
                        _mem_release(redis_lock_key)

        return wrapper
    return decorator
