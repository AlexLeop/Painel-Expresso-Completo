"""
Limpa TODAS as tabelas do schema public no Supabase via REST API.
Usa service_role key + cria funcao RPC temporaria para executar DDL.
"""

import httpx

SUPABASE_URL = "https://mdrutawgropwgsmwygtz.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1kcnV0YXdncm9wd2dzbXd5Z3R6Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTc0NTI3NSwiZXhwIjoyMDk3MzIxMjc1fQ.yOnMaVfpwksz_9TdufDMOVVDHIeZHTuuJGsM7uPiLMY"

HEADERS = {
    "apikey": SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
}

# Tabelas a preservar (PostGIS system tables)
PRESERVE = {"spatial_ref_sys", "geometry_columns", "geography_columns"}


def get_tables():
    """Lista tabelas via OpenAPI spec do PostgREST."""
    r = httpx.get(f"{SUPABASE_URL}/rest/v1/", headers=HEADERS, timeout=15)
    data = r.json()
    tables = sorted(data.get("definitions", {}).keys())
    return [t for t in tables if t not in PRESERVE]


def delete_all_rows(table_name):
    """DELETE all rows from a table via PostgREST."""
    r = httpx.delete(
        f"{SUPABASE_URL}/rest/v1/{table_name}",
        headers={**HEADERS, "Prefer": "return=representation"},
        params={"id": "neq.00000000-0000-0000-0000-000000000000"},  # Match all
        timeout=15,
    )
    return r.status_code, r.text[:200]


def drop_via_rpc():
    """
    Step 1: Cria uma funcao clean_schema() no Supabase
    Step 2: Chama via RPC
    Step 3: Remove a funcao

    Isso funciona porque service_role tem privilegio de criar funcoes.
    """
    # Step 1: Tentar usar o SQL endpoint da Supabase
    # A Supabase expoe um endpoint /sql para o service_role? Nao.
    # Mas podemos deletar cada tabela individualmente via REST DELETE

    tables = get_tables()
    print(f"Encontradas {len(tables)} tabelas para limpar:")
    for t in tables:
        print(f"  - {t}")

    print(f"\nTabelas preservadas (PostGIS): {PRESERVE}")
    print("\n=== INICIANDO LIMPEZA ===\n")

    # Approach: Deletar todos os registros de cada tabela
    # PostgREST nao suporta DROP TABLE, mas podemos limpar os dados
    for table in tables:
        # DELETE com filtro que pega tudo
        r = httpx.delete(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers={**HEADERS, "Prefer": "return=minimal"},
            # Filtro que pega TODOS os registros
            params={"or": "(id.not.is.null,id.is.null)"},
            timeout=15,
        )
        status = "OK" if r.status_code in (200, 204) else f"WARN({r.status_code})"
        print(f"  DELETE FROM {table}: {status}")
        if r.status_code not in (200, 204):
            # Tenta sem filtro
            r2 = httpx.delete(
                f"{SUPABASE_URL}/rest/v1/{table}",
                headers={**HEADERS, "Prefer": "return=minimal"},
                timeout=15,
            )
            status2 = (
                "OK"
                if r2.status_code in (200, 204)
                else f"FAIL({r2.status_code}: {r2.text[:100]})"
            )
            print(f"    Retry sem filtro: {status2}")

    print("\n=== LIMPEZA CONCLUIDA ===")
    print("NOTA: Os dados foram deletados mas as tabelas ainda existem.")
    print("Para dropar as tabelas, use o SQL Editor do Supabase Dashboard.")
    print("Copie e cole o seguinte SQL:\n")

    # Gera SQL para copiar e colar
    print("-- Cole isso no SQL Editor do Supabase Dashboard:")
    print("BEGIN;")
    for table in tables:
        print(f'DROP TABLE IF EXISTS public."{table}" CASCADE;')

    # Dropar funcoes RPC customizadas
    print("")
    print("-- Dropar funcoes customizadas")
    print("DO $$ DECLARE")
    print("  rec RECORD;")
    print("BEGIN")
    print("  FOR rec IN")
    print("    SELECT p.proname, pg_get_function_identity_arguments(p.oid) as args")
    print("    FROM pg_proc p")
    print("    JOIN pg_namespace n ON p.pronamespace = n.oid")
    print("    WHERE n.nspname = 'public'")
    print("    AND p.proname NOT LIKE 'st_%'")  # Preserva funcoes PostGIS
    print("    AND p.prokind = 'f'")
    print("  LOOP")
    print(
        "    EXECUTE format('DROP FUNCTION IF EXISTS public.%I(%s) CASCADE', rec.proname, rec.args);"
    )
    print("  END LOOP;")
    print("END $$;")
    print("")

    # Dropar types/enums
    print("-- Dropar enums customizados")
    print("DO $$ DECLARE")
    print("  rec RECORD;")
    print("BEGIN")
    print("  FOR rec IN")
    print("    SELECT typname FROM pg_type")
    print("    WHERE typnamespace = 'public'::regnamespace")
    print("    AND typtype = 'e'")
    print("  LOOP")
    print("    EXECUTE format('DROP TYPE IF EXISTS public.%I CASCADE', rec.typname);")
    print("  END LOOP;")
    print("END $$;")
    print("")
    print("COMMIT;")


if __name__ == "__main__":
    drop_via_rpc()
