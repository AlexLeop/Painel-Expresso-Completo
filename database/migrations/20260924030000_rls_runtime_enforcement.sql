-- Production RLS enforcement and narrowly scoped tenant resolvers for public webhooks.
-- Webhook endpoints authenticate at HTTP level, resolve an opaque resource to a tenant,
-- then continue under the ordinary tenant policies.

CREATE OR REPLACE FUNCTION public.resolve_store_integration_operator(target_id UUID)
RETURNS UUID
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT si.operator_id
      FROM public."StoreIntegration" AS si
     WHERE si.id = target_id
       AND si.active = TRUE
     LIMIT 1;
$$;

CREATE OR REPLACE FUNCTION public.resolve_withdrawal_operator(
    target_txid TEXT,
    target_e2e TEXT
)
RETURNS UUID
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT wr.operator_id
      FROM public."WithdrawalRequest" AS wr
     WHERE (target_txid IS NOT NULL AND wr."baasTransactionId" = target_txid)
        OR (target_e2e IS NOT NULL AND wr."baasTransactionId" = target_e2e)
     LIMIT 1;
$$;

-- The application role only learns the tenant UUID for an already known opaque ID.
-- No business data is exposed by these functions.
REVOKE ALL ON FUNCTION public.resolve_store_integration_operator(UUID) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.resolve_withdrawal_operator(TEXT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.resolve_store_integration_operator(UUID) TO PUBLIC;
GRANT EXECUTE ON FUNCTION public.resolve_withdrawal_operator(TEXT, TEXT) TO PUBLIC;

-- Ensure every tenant table has RLS enabled. The application health gate separately
-- rejects a runtime DB role that is superuser, BYPASSRLS, or owns an RLS table.
-- Keeping the deployment owner separate lets SECURITY DEFINER resolve the opaque
-- webhook resource while the runtime role remains subject to all tenant policies.
DO $$
DECLARE
    target RECORD;
BEGIN
    FOR target IN
        SELECT n.nspname AS schema_name, c.relname AS table_name
          FROM pg_class AS c
          JOIN pg_namespace AS n ON n.oid = c.relnamespace
         WHERE n.nspname = 'public'
           AND c.relkind IN ('r', 'p')
           AND EXISTS (
               SELECT 1
                 FROM information_schema.columns AS cols
                WHERE cols.table_schema = n.nspname
                  AND cols.table_name = c.relname
                  AND cols.column_name = 'operator_id'
           )
    LOOP
        EXECUTE format(
            'ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY',
            target.schema_name,
            target.table_name
        );
    END LOOP;
END $$;
