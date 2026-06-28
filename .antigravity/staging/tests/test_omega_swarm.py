import pytest
from pydantic import BaseModel, ValidationError, Field
from postgrest.exceptions import APIError
from ninja.errors import HttpError
import threading

import os
import sys

# Append staging directory to sys.path so we import the modified files!
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

# Test exceptions handler in api.py
def test_global_exception_handler_validation_error():
    from config.api import global_exception_handler
    
    class MockRequest:
        pass

    class DummyModel(BaseModel):
        id: int = Field(..., strict=True)
        
    try:
        DummyModel(id="not-an-int")
    except ValidationError as e:
        response = global_exception_handler(MockRequest(), e)
        assert response.status_code == 422
        import json
        content = json.loads(response.content)
        assert content["success"] is False
        assert "error" in content
        assert "details" in content

def test_global_exception_handler_api_error(mock_supabase_api_error_500):
    from config.api import global_exception_handler
    class MockRequest:
        pass
        
    try:
        mock_supabase_api_error_500()
    except APIError as e:
        response = global_exception_handler(MockRequest(), e)
        assert response.status_code == 502
        import json
        content = json.loads(response.content)
        assert content["success"] is False
        assert "duplicate key" in content["details"]["message"] or "Database Error" in content["details"]["message"]
        assert "stack_trace" not in content
        
def test_lazy_supabase_client():
    from config.supabase_client import get_supabase_client, _local
    # Reset local state for testing
    if hasattr(_local, "supabase"):
        del _local.supabase
        
    client = get_supabase_client()
    assert client is not None
    assert hasattr(_local, "supabase")
    assert _local.supabase is client
    
    # Assert it returns same on subsequent calls
    client2 = get_supabase_client()
    assert client2 is client

def test_supabase_jwt_auth_invalid_token():
    from config.api import SupabaseJWTAuth
    auth = SupabaseJWTAuth()
    class MockRequest:
        pass
        
    with pytest.raises(HttpError) as excinfo:
        auth.authenticate(MockRequest(), "invalid-token-string")
    
    assert excinfo.value.status_code == 401
    assert "Token inválido" in str(excinfo.value)
