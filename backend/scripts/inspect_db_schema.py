import psycopg

conn = psycopg.connect('postgres://postgres:Al147258%40%23@191.101.235.244:5433/expresso_neves?sslmode=disable')
cur = conn.cursor()

for table in ["Driver", "Vehicle", "DriverDocument", "Store", "Client", "Operator"]:
    print(f"\n=== {table} ===")
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position;", (table,))
    for col, dt in cur.fetchall():
        print(f"  {col}: {dt}")

conn.close()
