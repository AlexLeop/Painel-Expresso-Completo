import os
import psycopg

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    raise RuntimeError("DATABASE_URL não configurada no ambiente.")

conn = psycopg.connect(db_url)
cur = conn.cursor()

for table in ["Driver", "Vehicle", "DriverDocument", "Store", "Client", "Operator"]:
    print(f"\n=== {table} ===")
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position;", (table,))
    for col, dt in cur.fetchall():
        print(f"  {col}: {dt}")

conn.close()
