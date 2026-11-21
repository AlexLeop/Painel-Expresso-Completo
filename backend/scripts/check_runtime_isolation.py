"""Exercise canonical RLS using the same connection across transactions.

The script is for the disposable PostgreSQL and Redis services used by CI.
Database fixtures, role and changes are rolled back after the check.
"""

import json
import os
from uuid import uuid4

import psycopg
import redis


def check_database():
    database_url = os.environ["TEST_SCHEMA_DATABASE_URL"]
    first, second = uuid4(), uuid4()
    with psycopg.connect(database_url) as db:
        with db.cursor() as cursor:
            cursor.execute("CREATE ROLE neves_ci_runtime NOLOGIN NOSUPERUSER NOBYPASSRLS")
            cursor.execute("GRANT USAGE ON SCHEMA public TO neves_ci_runtime")
            cursor.execute('GRANT SELECT ON public."Driver" TO neves_ci_runtime')
            for operator_id in (first, second):
                cursor.execute('INSERT INTO public."Operator" (id, name) VALUES (%s, %s)', (operator_id, "CI"))
                cursor.execute(
                    'INSERT INTO public."Driver" (operator_id, name, phone, "pixKeyType", "pixKey") '
                    "VALUES (%s, 'CI', %s, 'PHONE', '')",
                    (operator_id, str(operator_id.int)[:18]),
                )
            cursor.execute("SET LOCAL ROLE neves_ci_runtime")
            for operator in (first, second, None):
                with db.transaction():
                    claims = {"app_metadata": {"operator_id": str(operator)}} if operator else {}
                    cursor.execute("SELECT set_config('request.jwt.claims', %s, true)", (json.dumps(claims),))
                    cursor.execute('SELECT DISTINCT operator_id FROM public."Driver"')
                    assert cursor.fetchall() == ([(operator,)] if operator else [])
            cursor.execute("SELECT set_config('request.jwt.claims', '', true)")
            cursor.execute('SELECT EXISTS (SELECT FROM public."Driver")')
            assert cursor.fetchone() == (False,)
        db.rollback()


def check_cache():
    cache = redis.Redis.from_url(os.environ["TEST_SCHEMA_REDIS_URL"])
    key = f"ci:runtime:{uuid4()}"
    assert cache.set(key, "checked", nx=True, ex=30)
    assert cache.get(key) == b"checked"
    cache.delete(key)


if __name__ == "__main__":
    check_database()
    check_cache()
    print("Canonical PostgreSQL RLS and Redis checks passed.")
