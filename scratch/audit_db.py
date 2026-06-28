import os
import psycopg
from urllib.parse import urlparse

# Get DB URL from .env
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

print(f"Connecting to: {direct_url.split('@')[1]}")

conn = psycopg.connect(direct_url)

# Helper function to print queries
def run_query(query, title):
    print(f"\n--- {title} ---")
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            if not rows:
                print("No results found.")
            for row in rows:
                print(row)
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()

# 1. Constraints on Position
run_query("""
SELECT conname, contype, pg_get_constraintdef(c.oid)
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
WHERE t.relname = 'Position';
""", "Constraints on Position table")

# 2. Constraints on IntegrationOutbox
run_query("""
SELECT conname, contype, pg_get_constraintdef(c.oid)
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
WHERE t.relname = 'IntegrationOutbox';
""", "Constraints on IntegrationOutbox table")

# 3. Sequences
run_query("""
SELECT relname FROM pg_class WHERE relkind = 'S' AND relname ILIKE '%outbox%';
""", "Sequences related to Outbox")

# 4. Indexes on IntegrationOutbox
run_query("""
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'IntegrationOutbox';
""", "Indexes on IntegrationOutbox")

# 5. Missing columns or constraints on Store?
run_query("""
SELECT conname, contype, pg_get_constraintdef(c.oid)
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
WHERE t.relname = 'Store';
""", "Constraints on Store table")

# 6. Check for Position table partitions
run_query("""
SELECT i.inhrelid::regclass AS child
FROM pg_inherits i
JOIN pg_class p ON i.inhparent = p.oid
WHERE p.relname = 'Position';
""", "Partitions of Position table")

# 7. Integration Event Audit table
run_query("""
SELECT conname, contype, pg_get_constraintdef(c.oid)
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
WHERE t.relname = 'IntegrationEventAudit';
""", "Constraints on IntegrationEventAudit table")

conn.close()
