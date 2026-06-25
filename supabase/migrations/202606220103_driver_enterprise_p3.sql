-- ============================================================================
-- DRIVER ENTERPRISE P3
-- Compliance / LGPD: documentos versionados e aceite do motorista
-- ============================================================================

CREATE TABLE IF NOT EXISTS "ComplianceDocument" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    "audienceType" VARCHAR(20) NOT NULL DEFAULT 'DRIVER',
    code VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    body TEXT NOT NULL,
    required BOOLEAN NOT NULL DEFAULT TRUE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    "effectiveAt" TIMESTAMP WITH TIME ZONE NOT NULL,
    "archivedAt" TIMESTAMP WITH TIME ZONE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_compliance_document_version UNIQUE (operator_id, "audienceType", code, version)
);

CREATE INDEX IF NOT EXISTS idx_compliance_document_lookup
ON "ComplianceDocument"(operator_id, "audienceType", active, "effectiveAt" DESC);

CREATE TABLE IF NOT EXISTS "DriverConsentAcceptance" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES "ComplianceDocument"(id) ON DELETE CASCADE,
    "deviceIdentifier" VARCHAR(255),
    "ipAddress" VARCHAR(64),
    "userAgent" TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    "acceptedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_driver_document_acceptance UNIQUE (driver_id, document_id)
);

CREATE INDEX IF NOT EXISTS idx_driver_consent_acceptance_driver
ON "DriverConsentAcceptance"(operator_id, driver_id, "acceptedAt" DESC);

ALTER TABLE "ComplianceDocument" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "DriverConsentAcceptance" ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    BEGIN
        CREATE POLICY "Isolamento de Tenant - ComplianceDocument" ON "ComplianceDocument"
        AS PERMISSIVE FOR ALL
        USING (is_platform_admin() OR operator_id = current_operator_id());
    EXCEPTION WHEN duplicate_object THEN NULL;
    END;

    BEGIN
        CREATE POLICY "Isolamento de Tenant - DriverConsentAcceptance" ON "DriverConsentAcceptance"
        AS PERMISSIVE FOR ALL
        USING (is_platform_admin() OR operator_id = current_operator_id());
    EXCEPTION WHEN duplicate_object THEN NULL;
    END;
END $$;
