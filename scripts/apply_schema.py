import psycopg
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Migration and Schema operations should ALWAYS use the session pooler
# which the user provided as DIRECT_URL (port 5432).
# The default DATABASE_URL points to the transaction pooler (port 6543) which breaks DDL.
direct_url = os.environ.get('DIRECT_URL')

def apply_schema(conn):
    project_root = Path(__file__).resolve().parent.parent
    migrations_dir = project_root / "supabase" / "migrations"
    migration_paths = sorted(migrations_dir.glob("*.sql"))

    if not migration_paths:
        print("ERRO: nenhuma migration SQL encontrada.")
        return False

    for schema_path in migration_paths:
        with open(schema_path, "r", encoding="utf-8") as f:
            sql = f.read()

        print(f"\nAplicando migration {schema_path.name} ({len(sql)} bytes)...")
        try:
            conn.execute(sql)
        except Exception as e:
            print(f"ERRO ao aplicar {schema_path.name}: {e}")
            return False

    print("Todas as migrations SQL foram aplicadas com sucesso!")
    return True

if __name__ == "__main__":
    if not direct_url:
        print("ERRO: DIRECT_URL não definido no .env!")
        sys.exit(1)
        
    print(f"=== Conectando ao Banco via DIRECT_URL (Session Pooler) ===")
    try:
        conn = psycopg.connect(direct_url, autocommit=True)
        row = conn.execute("SELECT version()").fetchone()
        if row:
            print("Conectado! PostgreSQL:", row[0][:60])
        
        apply_schema(conn)
        
        print("\nSchema aplicado com sucesso! Agora você pode rodar as migrations do Django.")
        
    except Exception as e:
        print(f"ERRO: {e}")
