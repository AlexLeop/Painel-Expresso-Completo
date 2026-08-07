import os
import psycopg
from urllib.parse import urlparse

env_file = r"c:\Users\lxleo\Documents\Expresso Neves\Painel Expresso Neves e Django DRF\.env"
direct_url = None
with open(env_file, "r") as f:
    for line in f:
        if line.startswith("DIRECT_URL="):
            direct_url = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

if not direct_url:
    print("DIRECT_URL not found")
    exit(1)

conn = psycopg.connect(direct_url)
conn.autocommit = True

def run_ddl(sql, description):
    print(f"Executing: {description}")
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        print("[SUCCESS]")
    except Exception as e:
        print(f"[FAILED] {e}")
        # Note: psycopg automatically manages transactions, but we use autocommit=True for CONCURRENTLY

# 1. Clean duplicates in Position (Keep the one with lowest id)
run_ddl("""
DELETE FROM "Position" p1
USING "Position" p2
WHERE p1.driver_id = p2.driver_id 
  AND p1."capturedAt" = p2."capturedAt" 
  AND p1.id > p2.id;
""", "Limpar duplicados em Position")

# 2. Add Unique Constraint to Position
run_ddl("""
ALTER TABLE "Position" ADD CONSTRAINT unique_driver_captured_at UNIQUE (driver_id, "capturedAt");
""", "Adicionar UNIQUE constraint em Position (driver_id, capturedAt)")

# 3. Clean duplicates in Store
run_ddl("""
DELETE FROM "Store" s1
USING "Store" s2
WHERE s1.client_id = s2.client_id 
  AND s1.operator_id = s2.operator_id
  AND s1.name = s2.name
  AND s1.id > s2.id;
""", "Limpar duplicados em Store")

# 4. Add Unique Constraint to Store
run_ddl("""
ALTER TABLE "Store" ADD CONSTRAINT unique_store_client_operator_name UNIQUE (client_id, operator_id, name);
""", "Adicionar UNIQUE constraint em Store")

# 5. Add Index for IntegrationOutbox for backoff query
run_ddl("""
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_outbox_retry ON "IntegrationOutbox" (status, "lastAttemptAt");
""", "Adicionar idx_outbox_retry em IntegrationOutbox")

conn.close()
