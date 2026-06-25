-- ============================================================================
-- Driver / Client Enterprise P2
-- Redistribuicao auditavel e comunicacao operacional persistida
-- ============================================================================

CREATE TABLE IF NOT EXISTS "OrderAssignmentAudit" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    order_id UUID NOT NULL REFERENCES "Order"(id) ON DELETE CASCADE,
    previous_driver_id UUID REFERENCES "Driver"(id) ON DELETE SET NULL,
    new_driver_id UUID REFERENCES "Driver"(id) ON DELETE SET NULL,
    changed_by_staff_id UUID REFERENCES "StaffMember"(id) ON DELETE SET NULL,
    changed_by_client_id UUID REFERENCES "ClientPortalUser"(id) ON DELETE SET NULL,
    reason TEXT NOT NULL,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT order_assignment_actor_xor CHECK (num_nonnulls(changed_by_staff_id, changed_by_client_id) = 1)
);
CREATE INDEX IF NOT EXISTS idx_order_assignment_audit_order
ON "OrderAssignmentAudit"(operator_id, order_id, "createdAt" DESC);

CREATE TABLE IF NOT EXISTS "DriverCommunicationThread" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    order_id UUID REFERENCES "Order"(id) ON DELETE SET NULL,
    store_id UUID REFERENCES "Store"(id) ON DELETE SET NULL,
    driver_id UUID NOT NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    "sourceType" VARCHAR(20) NOT NULL DEFAULT 'STORE',
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    subject VARCHAR(255),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_driver_communication_thread_driver
ON "DriverCommunicationThread"(operator_id, driver_id, status, "updatedAt" DESC);

CREATE TABLE IF NOT EXISTS "DriverCommunicationMessage" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    thread_id UUID NOT NULL REFERENCES "DriverCommunicationThread"(id) ON DELETE CASCADE,
    "senderType" VARCHAR(20) NOT NULL,
    "senderName" VARCHAR(255),
    message TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_driver_communication_message_thread
ON "DriverCommunicationMessage"(operator_id, thread_id, "createdAt" DESC);

ALTER TABLE "OrderAssignmentAudit" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "DriverCommunicationThread" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "DriverCommunicationMessage" ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'OrderAssignmentAudit'
        AND policyname = 'Isolamento de Tenant - OrderAssignmentAudit'
    ) THEN
        CREATE POLICY "Isolamento de Tenant - OrderAssignmentAudit" ON "OrderAssignmentAudit"
        USING (operator_id = current_operator_id())
        WITH CHECK (operator_id = current_operator_id());
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'DriverCommunicationThread'
        AND policyname = 'Isolamento de Tenant - DriverCommunicationThread'
    ) THEN
        CREATE POLICY "Isolamento de Tenant - DriverCommunicationThread" ON "DriverCommunicationThread"
        USING (operator_id = current_operator_id())
        WITH CHECK (operator_id = current_operator_id());
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'DriverCommunicationMessage'
        AND policyname = 'Isolamento de Tenant - DriverCommunicationMessage'
    ) THEN
        CREATE POLICY "Isolamento de Tenant - DriverCommunicationMessage" ON "DriverCommunicationMessage"
        USING (operator_id = current_operator_id())
        WITH CHECK (operator_id = current_operator_id());
    END IF;
END $$;
