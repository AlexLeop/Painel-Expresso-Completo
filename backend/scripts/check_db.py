import os
import psycopg

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    from pathlib import Path
    env_file = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                DATABASE_URL = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

if not DATABASE_URL:
    raise ValueError("DATABASE_URL não configurada no ambiente ou no arquivo .env.")

with psycopg.connect(DATABASE_URL) as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT id, email, supabase_uid FROM "PlatformAdmin"')
        for row in cur.fetchall():
            print(row)
