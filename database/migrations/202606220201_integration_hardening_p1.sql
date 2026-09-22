-- ============================================================================
-- Integration Hardening P1
-- Business audit for inbound/outbound partner confirmations
-- ============================================================================

CREATE TABLE IF NOT EXISTS "IntegrationEventAudit" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    store_id UUID NOT NULL REFERENCES "Store"(id) ON DELETE CASCADE,
    order_id UUID REFERENCES "Order"(id) ON DELETE SET NULL,
    provider VARCHAR(50) NOT NULL,
    direction VARCHAR(20) NOT NULL,
    "eventType" VARCHAR(100) NOT NULL,
    "externalOrderId" VARCHAR(255),
    "merchantReference" VARCHAR(100),
    "deliveryStatus" VARCHAR(30) NOT NULL,
    "httpStatusCode" INT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    "responsePayload" JSONB NOT NULL DEFAULT '{}'::jsonb,
    "failReason" TEXT,
    "processedAt" TIMESTAMP WITH TIME ZONE,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_integration_event_audit_lookup
ON "IntegrationEventAudit"(operator_id, store_id, provider, direction, "createdAt" DESC);
CREATE INDEX IF NOT EXISTS idx_integration_event_audit_order
ON "IntegrationEventAudit"(operator_id, order_id, "createdAt" DESC);

ALTER TABLE "IntegrationEventAudit" ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'IntegrationEventAudit'
        AND policyname = 'Isolamento de Tenant - IntegrationEventAudit'
    ) THEN
        CREATE POLICY "Isolamento de Tenant - IntegrationEventAudit" ON "IntegrationEventAudit"
        USING (operator_id = current_operator_id())
        WITH CHECK (operator_id = current_operator_id());
    END IF;
END $$;
