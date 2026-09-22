-- ============================================================================
-- Integration Hardening P2
-- Transport config per provider + external event tracking
-- ============================================================================

ALTER TABLE "StoreIntegration"
    ADD COLUMN IF NOT EXISTS "authMode" VARCHAR(30) NOT NULL DEFAULT 'WEBHOOK',
    ADD COLUMN IF NOT EXISTS "baseUrl" TEXT,
    ADD COLUMN IF NOT EXISTS "webhookUrl" TEXT;

ALTER TABLE "IntegrationEventAudit"
    ADD COLUMN IF NOT EXISTS "externalEventId" VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_integration_event_audit_external_event
ON "IntegrationEventAudit"(operator_id, provider, "externalEventId");
