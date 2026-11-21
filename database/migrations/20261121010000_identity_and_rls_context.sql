-- Correct normalization without changing previously applied migration files.
-- Duplicate legacy identities must be reconciled explicitly before deployment.
DO $$
BEGIN
    IF EXISTS (
        SELECT regexp_replace(phone, '[^0-9]', '', 'g')
        FROM public."Driver"
        WHERE active AND regexp_replace(phone, '[^0-9]', '', 'g') <> ''
        GROUP BY regexp_replace(phone, '[^0-9]', '', 'g') HAVING COUNT(*) > 1
    ) OR EXISTS (
        SELECT regexp_replace(document, '[^0-9]', '', 'g')
        FROM public."Driver"
        WHERE active AND document IS NOT NULL
          AND regexp_replace(document, '[^0-9]', '', 'g') <> ''
        GROUP BY regexp_replace(document, '[^0-9]', '', 'g') HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Duplicate normalized driver identities require reconciliation before migration';
    END IF;
END $$;

DROP INDEX IF EXISTS public.uq_driver_active_phone_identity;
DROP INDEX IF EXISTS public.uq_driver_active_document_identity;
CREATE UNIQUE INDEX uq_driver_active_phone_identity
    ON public."Driver" ((regexp_replace(phone, '[^0-9]', '', 'g')))
    WHERE active AND regexp_replace(phone, '[^0-9]', '', 'g') <> '';
CREATE UNIQUE INDEX uq_driver_active_document_identity
    ON public."Driver" ((regexp_replace(document, '[^0-9]', '', 'g')))
    WHERE active AND document IS NOT NULL
      AND regexp_replace(document, '[^0-9]', '', 'g') <> '';

CREATE OR REPLACE FUNCTION public.current_operator_id() RETURNS UUID AS $$
    SELECT NULLIF(
        NULLIF(current_setting('request.jwt.claims', true), '')::jsonb
            ->'app_metadata'->>'operator_id', ''
    )::uuid;
$$ LANGUAGE SQL STABLE;

-- Auth may locate a tenant before credentials are verified. This resolver
-- returns only its UUID. Normal policies still govern all business queries.
CREATE OR REPLACE FUNCTION public.native_auth_operator(identity_key TEXT)
RETURNS UUID LANGUAGE SQL STABLE SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT operator_id FROM (
        SELECT s.operator_id FROM public."StaffMember" s
        WHERE s.active AND (lower(s.email) = lower(identity_key) OR s.id::text = identity_key)
        UNION ALL
        SELECT u.operator_id FROM public."ClientPortalUser" u
        WHERE u.active AND (lower(u.email) = lower(identity_key) OR u.id::text = identity_key)
    ) identities LIMIT 1;
$$;

CREATE OR REPLACE FUNCTION public.is_platform_admin() RETURNS BOOLEAN AS $$
    SELECT COALESCE(
        (NULLIF(current_setting('request.jwt.claims', true), '')::jsonb
            ->'app_metadata'->>'role') = 'platform_admin', FALSE
    );
$$ LANGUAGE SQL STABLE;
