import os
import logging
from typing import Optional
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Fallbacks reais para garantir o funcionamento caso o usuário esqueça de configurar no painel
DEFAULT_URL = "https://mdrutawgropwgsmwygtz.supabase.co"
DEFAULT_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1kcnV0YXdncm9wd2dzbXd5Z3R6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE3NDUyNzUsImV4cCI6MjA5NzMyMTI3NX0.EVGv7fEupCR3Ru4wAffCeeR2Uq5Bl_HQxvJUY2HV3T0"

url: str = os.environ.get("SUPABASE_URL", DEFAULT_URL)
key: str = os.environ.get("SUPABASE_KEY", DEFAULT_KEY)
service_role_key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

supabase: Optional[Client] = None
_supabase_admin: Optional[Client] = None

# Default client (usually uses anon key or service role key if needed)
if url and key:
    try:
        supabase = create_client(url, key)
    except Exception as e:
        logger.error(f"Erro ao inicializar cliente Supabase: {e}")
        supabase = None
else:
    logger.warning("SUPABASE_URL ou SUPABASE_KEY não configurados e os defaults falharam.")

def get_supabase_admin() -> Client:
    """Lazy initialize and return the Supabase admin client using the service role key."""
    global _supabase_admin
    if _supabase_admin is not None:
        return _supabase_admin
        
    admin_url = os.environ.get("SUPABASE_URL")
    admin_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not admin_url or not admin_key:
        raise ValueError("SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY devem estar configurados para usar o admin client.")
        
    try:
        _supabase_admin = create_client(admin_url, admin_key)
        return _supabase_admin
    except Exception as e:
        logger.error(f"Erro ao inicializar Supabase Admin client: {e}")
        raise
