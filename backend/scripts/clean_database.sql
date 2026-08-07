-- ============================================================
-- LIMPEZA COMPLETA DO BANCO SUPABASE
-- Projeto: mdrutawgropwgsmwygtz
-- Execute este SQL no SQL Editor do Supabase Dashboard:
-- https://supabase.com/dashboard/project/mdrutawgropwgsmwygtz/sql/new
-- ============================================================

BEGIN;

-- 1. Drop tabelas do projeto anterior (Fleetbase migration)
DROP TABLE IF EXISTS public."payloads" CASCADE;
DROP TABLE IF EXISTS public."positions" CASCADE;
DROP TABLE IF EXISTS public."purchase_rates" CASCADE;
DROP TABLE IF EXISTS public."service_quote_items" CASCADE;
DROP TABLE IF EXISTS public."service_quotes" CASCADE;
DROP TABLE IF EXISTS public."service_rate_fees" CASCADE;
DROP TABLE IF EXISTS public."service_rate_parcel_fees" CASCADE;
DROP TABLE IF EXISTS public."service_rates" CASCADE;
DROP TABLE IF EXISTS public."services" CASCADE;
DROP TABLE IF EXISTS public."tracking_numbers" CASCADE;
DROP TABLE IF EXISTS public."tracking_statuses" CASCADE;
DROP TABLE IF EXISTS public."vehicles" CASCADE;
DROP TABLE IF EXISTS public."vendors" CASCADE;
DROP TABLE IF EXISTS public."waypoints" CASCADE;
DROP TABLE IF EXISTS public."zones" CASCADE;

-- 2. Drop todas as funcoes customizadas (preserva PostGIS st_*)
DO $$ DECLARE
  rec RECORD;
BEGIN
  FOR rec IN
    SELECT p.proname, pg_get_function_identity_arguments(p.oid) as args
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'public'
    AND p.proname NOT LIKE 'st_%'
    AND p.prokind = 'f'
  LOOP
    EXECUTE format('DROP FUNCTION IF EXISTS public.%I(%s) CASCADE', rec.proname, rec.args);
  END LOOP;
END $$;

-- 3. Drop todos os enums/types customizados
DO $$ DECLARE
  rec RECORD;
BEGIN
  FOR rec IN
    SELECT typname FROM pg_type
    WHERE typnamespace = 'public'::regnamespace
    AND typtype = 'e'
  LOOP
    EXECUTE format('DROP TYPE IF EXISTS public.%I CASCADE', rec.typname);
  END LOOP;
END $$;

-- 4. Drop todas as sequences orfas
DO $$ DECLARE
  rec RECORD;
BEGIN
  FOR rec IN
    SELECT sequencename FROM pg_sequences
    WHERE schemaname = 'public'
  LOOP
    EXECUTE format('DROP SEQUENCE IF EXISTS public.%I CASCADE', rec.sequencename);
  END LOOP;
END $$;

COMMIT;

-- Verificacao pos-limpeza:
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
