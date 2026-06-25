import os
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

url: str = os.environ.get("SUPABASE_URL", "")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY", "")

supabase: Client = None

if url and key:
    try:
        supabase = create_client(url, key)
    except Exception as e:
        logger.error(f"Erro ao inicializar Supabase client: {e}")
else:
    logger.warning("SUPABASE_URL ou SUPABASE_KEY não configurados. Fallback de storage ativo.")
