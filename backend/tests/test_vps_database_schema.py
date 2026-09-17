import os
import pytest
import psycopg
from urllib.parse import urlparse, unquote

def get_vps_db_url():
    # Priority: DATABASE_URL, then URL_EXTERNA from env
    url = os.environ.get("DATABASE_URL")
    if not url or "supabase" in url:
        url = os.environ.get("URL_EXTERNA")
    return url

@pytest.mark.vps_db
def test_vps_postgres_connection_and_postgis():
    db_url = get_vps_db_url()
    assert db_url, "No VPS database URL found in environment"
    
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            assert "PostgreSQL" in version
            
            cur.execute("SELECT PostGIS_Version();")
            postgis_ver = cur.fetchone()[0]
            assert "3.5" in postgis_ver or "3." in postgis_ver

@pytest.mark.vps_db
def test_vps_required_tables_exist():
    db_url = get_vps_db_url()
    assert db_url, "No VPS database URL found in environment"
    
    expected_tables = [
        "Operator",
        "PlatformAdmin",
        "StaffMember",
        "Store",
        "Driver",
        "Order",
        "Wallet",
        "WalletTransaction",
        "OperatorInternalWallet",
        "WithdrawalRequest",
        "PayoutPolicyConfig",
        "ServiceZone",
    ]
    
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = {row[0] for row in cur.fetchall()}
            
            for expected in expected_tables:
                assert expected in tables, f"Expected table '{expected}' not found in VPS database!"

@pytest.mark.vps_db
def test_vps_auth_password_hash_columns():
    db_url = get_vps_db_url()
    assert db_url, "No VPS database URL found in environment"
    
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name, column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND column_name = 'passwordHash'
            """)
            cols = {row[0] for row in cur.fetchall()}
            assert "PlatformAdmin" in cols, "'passwordHash' missing on PlatformAdmin"
            assert "StaffMember" in cols, "'passwordHash' missing on StaffMember"
