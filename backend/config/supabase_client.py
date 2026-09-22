"""
DEPRECATED: Supabase foi descontinuado.
O sistema opera em PostgreSQL 17 + PostGIS Standalone com autenticação nativa e storage local.
Este arquivo permanece apenas para compatibilidade regressiva de imports legados.
"""
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

supabase: Optional[Any] = None
_supabase_admin: Optional[Any] = None


def get_supabase_client() -> Optional[Any]:
    """Retorna None informando descontinuação do Supabase."""
    logger.debug("[SupabaseClient] get_supabase_client chamado, mas o Supabase foi descontinuado.")
    return None


def get_supabase_admin() -> Optional[Any]:
    """Retorna None informando descontinuação do Supabase."""
    logger.debug("[SupabaseClient] get_supabase_admin chamado, mas o Supabase foi descontinuado.")
    return None
