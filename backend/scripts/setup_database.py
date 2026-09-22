"""
Database Setup & Migration Runner for Standalone PostgreSQL 17 + PostGIS 3.5.

Executes all 16 SQL migrations in order, tracks applied migrations,
and applies native authentication schema patches.
"""

import os
import sys
from pathlib import Path
from typing import cast, LiteralString
from urllib.parse import urlparse, unquote
import psycopg

# Resolve root directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MIGRATIONS_DIR = BASE_DIR / "database" / "migrations"


def get_connection_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        # Load from .env if possible
        env_file = BASE_DIR / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("DATABASE_URL="):
                    url = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
                elif line.startswith("URL_EXTERNA=") and not url:
                    url = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not url:
        raise ValueError("Could not find DATABASE_URL or URL_EXTERNA in environment or .env")
    return url


def run_migrations():
    db_url = get_connection_url()
    parsed = urlparse(db_url)
    print(f"[*] Connecting to database '{parsed.path[1:]}' at {parsed.hostname}:{parsed.port}...")

    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            # 1. Verify extensions
            print("[*] Ensuring required PostgreSQL extensions are installed...")
            cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
            cur.execute('CREATE EXTENSION IF NOT EXISTS "postgis";')
            cur.execute("SELECT version(), PostGIS_Version();")
            ver_row = cur.fetchone()
            if ver_row:
                pg_ver, postgis_ver = ver_row
                print(f"[+] PostgreSQL Version: {str(pg_ver).split(',')[0]}")
                print(f"[+] PostGIS Version: {postgis_ver}")

            # 2. Setup migrations tracking table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS "_migrations" (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)

            cur.execute('SELECT name FROM "_migrations";')
            applied = {row[0] for row in cur.fetchall()}

            # 3. Read and execute migration files
            migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"), key=lambda p: p.name)
            if not migration_files:
                raise FileNotFoundError(f"No .sql files found in {MIGRATIONS_DIR}")

            print(f"[*] Found {len(migration_files)} migration files in {MIGRATIONS_DIR}")

            for sql_file in migration_files:
                if sql_file.name in applied:
                    print(f"  [-] Already applied: {sql_file.name}")
                    continue

                print(f"  [>] Applying migration: {sql_file.name}...")
                sql_content = sql_file.read_text(encoding="utf-8")

                with conn.transaction():
                    cur.execute(cast(LiteralString, sql_content))
                    cur.execute('INSERT INTO "_migrations" (name) VALUES (%s);', (sql_file.name,))

                print(f"  [+] Success: {sql_file.name}")

            # 4. Native Auth Schema Patches
            print("[*] Applying Native Auth Schema Patches (passwordHash and nullable supabase_uid)...")
            native_auth_patches = """
                -- PlatformAdmin
                ALTER TABLE "PlatformAdmin" ALTER COLUMN supabase_uid DROP NOT NULL;
                ALTER TABLE "PlatformAdmin" ALTER COLUMN supabase_uid SET DEFAULT uuid_generate_v4();
                ALTER TABLE "PlatformAdmin" ADD COLUMN IF NOT EXISTS "passwordHash" VARCHAR(255);

                -- StaffMember
                ALTER TABLE "StaffMember" ALTER COLUMN supabase_uid DROP NOT NULL;
                ALTER TABLE "StaffMember" ALTER COLUMN supabase_uid SET DEFAULT uuid_generate_v4();
                ALTER TABLE "StaffMember" ADD COLUMN IF NOT EXISTS "passwordHash" VARCHAR(255);

                -- Driver
                ALTER TABLE "Driver" ALTER COLUMN supabase_uid DROP NOT NULL;
                ALTER TABLE "Driver" ALTER COLUMN supabase_uid SET DEFAULT uuid_generate_v4();
                ALTER TABLE "Driver" ADD COLUMN IF NOT EXISTS "passwordHash" VARCHAR(255);

                -- ClientPortalUser
                ALTER TABLE "ClientPortalUser" ALTER COLUMN supabase_uid DROP NOT NULL;
                ALTER TABLE "ClientPortalUser" ALTER COLUMN supabase_uid SET DEFAULT uuid_generate_v4();
                ALTER TABLE "ClientPortalUser" ADD COLUMN IF NOT EXISTS "passwordHash" VARCHAR(255);

                -- Operator SaaS & Billing Configuration
                ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS phone VARCHAR(50);
                ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS city VARCHAR(100);
                ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS state VARCHAR(10);
                ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS "billingPlanType" VARCHAR(50) DEFAULT 'PERCENT_PER_DELIVERY';
                ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS "billingRateValue" NUMERIC(10,2) DEFAULT 0.00;
                ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS "billingCycle" VARCHAR(30) DEFAULT 'MENSAL';
                ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS "dueDay" INTEGER DEFAULT 10;
                ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS "trialDays" INTEGER DEFAULT 14;
                ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS "gracePeriodDays" INTEGER DEFAULT 5;
                ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS notes TEXT;
            """
            with conn.transaction():
                cur.execute(cast(LiteralString, native_auth_patches))
            print("[+] Native Auth & Operator SaaS Patches successfully applied!")

            # 5. Schema verification summary
            cur.execute("""
                SELECT count(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public';
            """)
            count_row = cur.fetchone()
            table_count = count_row[0] if count_row else 0
            print(f"\n[OK] VPS Database Migration Complete! Total public tables: {table_count}")


if __name__ == "__main__":
    run_migrations()
