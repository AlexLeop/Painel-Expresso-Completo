-- ============================================================================
-- INIT.SQL: Bootstrap do Banco para Ambiente Docker Local
-- Executa automaticamente na primeira inicialização do container PostgreSQL.
-- Cria as roles do Supabase, extensões e aplica o schema de negócio.
-- ============================================================================

-- 1. Criar as Roles que o Supabase cria automaticamente em produção
-- (PostgreSQL vanilla não as possui)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        CREATE ROLE anon NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        CREATE ROLE authenticated NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        CREATE ROLE service_role NOLOGIN;
    END IF;
END $$;

-- 2. Conceder permissões mínimas para as roles operarem via RLS
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated, service_role;

-- Permissões default para tabelas futuras
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO authenticated, service_role;

-- 3. Permitir que o user postgres possa fazer SET ROLE para essas roles
GRANT anon TO postgres;
GRANT authenticated TO postgres;
GRANT service_role TO postgres;

-- 4. Configuração de variáveis de sessão (simula o request.jwt.claims do Supabase)
-- Necessário para que set_config('request.jwt.claims', ...) funcione sem erros
ALTER DATABASE postgres SET "request.jwt.claims" TO '';
