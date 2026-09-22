ALTER TABLE "DriverConsentAcceptance"
    ADD COLUMN IF NOT EXISTS "revokedAt" TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS "revokedReason" TEXT;

CREATE TABLE IF NOT EXISTS "PrivacyDataRequest" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    "subjectType" VARCHAR(30) NOT NULL DEFAULT 'DRIVER',
    driver_id UUID REFERENCES "Driver"(id) ON DELETE CASCADE,
    client_portal_user_id UUID REFERENCES "ClientPortalUser"(id) ON DELETE CASCADE,
    "requestType" VARCHAR(30) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'OPEN',
    description TEXT NOT NULL,
    resolution TEXT,
    "resolvedAt" TIMESTAMP WITH TIME ZONE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT privacy_data_request_subject_xor CHECK (num_nonnulls(driver_id, client_portal_user_id) = 1),
    CONSTRAINT privacy_data_request_request_type_not_blank CHECK (char_length("requestType") > 0)
);

CREATE INDEX IF NOT EXISTS idx_privacy_data_request_lookup
ON "PrivacyDataRequest"(operator_id, status, "subjectType", "createdAt" DESC);

CREATE TABLE IF NOT EXISTS "ComplianceRetentionPolicy" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    "resourceType" VARCHAR(50) NOT NULL,
    "retentionDays" INT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    "lastExecutedAt" TIMESTAMP WITH TIME ZONE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT compliance_retention_policy_days_positive CHECK ("retentionDays" > 0),
    CONSTRAINT unique_compliance_retention_policy_resource UNIQUE (operator_id, "resourceType")
);

CREATE INDEX IF NOT EXISTS idx_compliance_retention_policy_lookup
ON "ComplianceRetentionPolicy"(operator_id, active, "resourceType");

ALTER TABLE "PrivacyDataRequest" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "ComplianceRetentionPolicy" ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'PrivacyDataRequest'
        AND policyname = 'Isolamento de Tenant - PrivacyDataRequest'
    ) THEN
        CREATE POLICY "Isolamento de Tenant - PrivacyDataRequest" ON "PrivacyDataRequest"
        USING (operator_id = current_operator_id())
        WITH CHECK (operator_id = current_operator_id());
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'ComplianceRetentionPolicy'
        AND policyname = 'Isolamento de Tenant - ComplianceRetentionPolicy'
    ) THEN
        CREATE POLICY "Isolamento de Tenant - ComplianceRetentionPolicy" ON "ComplianceRetentionPolicy"
        USING (operator_id = current_operator_id())
        WITH CHECK (operator_id = current_operator_id());
    END IF;
END $$;
