import pytest
import httpx
from postgrest.exceptions import APIError
from unittest.mock import patch, MagicMock
import os
import sys

# PRIORITY: Load modules from staging first to test the fixes before merging!
staging_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if staging_dir not in sys.path:
    sys.path.insert(0, staging_dir)
# MOCKS EXIGIDOS PELO RED TEAM (OMEGA SWARM v2.1)
# ==========================================

@pytest.fixture
def mock_httpx_fork_collapse():
    """
    Cenário 1: Simula o colapso do multiplexing HTTP/2 em instâncias 
    globais de httpx.Client clonadas via fork (Celery).
    """
    with patch("httpx.Client.send") as mock_send:
        # Quando o child-process tenta usar o socket copiado, levanta NetworkError
        mock_send.side_effect = httpx.NetworkError("Socket connection broken by fork")
        yield mock_send

@pytest.fixture
def mock_supabase_storage_timeout():
    """
    Cenário 2: Simula timeout direto no signing do storage, que utiliza 
    a SERVICE_ROLE_KEY local. Avaliará se a chave está escapando no stack trace.
    """
    with patch("httpx.post") as mock_post:
        # Timeout ao tentar assinar a URL da CNH
        mock_post.side_effect = httpx.TimeoutException("Supabase Storage timeout")
        yield mock_post

@pytest.fixture
def mock_supabase_api_error_500():
    """
    Cenário 3: Simula falha na escrita simultânea ou erro nativo do PostgREST.
    """
    def _raise_error(*args, **kwargs):
        error_payload = {
            "code": "23505",
            "details": "Key (id)=(1) already exists.",
            "hint": None,
            "message": "duplicate key value violates unique constraint"
        }
        raise APIError(error_payload)
    return _raise_error
