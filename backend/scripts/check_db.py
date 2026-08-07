import psycopg

DATABASE_URL = 'postgresql://postgres.mdrutawgropwgsmwygtz:91203095_%23%23%40@aws-1-us-west-2.pooler.supabase.com:5432/postgres'

with psycopg.connect(DATABASE_URL) as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT id, email, supabase_uid FROM "PlatformAdmin"')
        for row in cur.fetchall():
            print(row)
