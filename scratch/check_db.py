import psycopg2
import os

DATABASE_URL = "postgresql://postgres.mdrutawgropwgsmwygtz:cad35b2f3964e05fd894@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

cur.execute("SELECT id, email, supabase_uid FROM accounts_platformadmin")
admins = cur.fetchall()
print("--- Platform Admins ---")
for admin in admins:
    print(admin)

cur.execute("SELECT id, email, supabase_uid FROM accounts_staffmember")
staff = cur.fetchall()
print("\n--- Staff Members ---")
for s in staff:
    print(s)

cur.close()
conn.close()
