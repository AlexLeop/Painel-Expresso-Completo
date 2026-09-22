-- ============================================================================
-- DRIVER ENTERPRISE P1
-- Performance, agenda, dispositivos, segurança mobile, offline sync e despesas
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'driver_shift_reservation_status') THEN
        CREATE TYPE driver_shift_reservation_status AS ENUM (
            'REQUESTED',
            'CONFIRMED',
            'CANCELED'
        );
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'driver_device_status') THEN
        CREATE TYPE driver_device_status AS ENUM (
            'ACTIVE',
            'REVOKED'
        );
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'driver_security_risk_level') THEN
        CREATE TYPE driver_security_risk_level AS ENUM (
            'LOW',
            'MEDIUM',
            'HIGH',
            'CRITICAL'
        );
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'offline_sync_status') THEN
        CREATE TYPE offline_sync_status AS ENUM (
            'RECEIVED',
            'PROCESSED',
            'FAILED'
        );
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'driver_expense_type') THEN
        CREATE TYPE driver_expense_type AS ENUM (
            'FUEL',
            'TOLL',
            'PARKING',
            'OTHER'
        );
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'driver_expense_status') THEN
        CREATE TYPE driver_expense_status AS ENUM (
            'SUBMITTED',
            'APPROVED',
            'REJECTED'
        );
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS "DriverShiftReservation" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    store_id UUID NOT NULL REFERENCES "Store"(id) ON DELETE CASCADE,
    turno_id UUID NOT NULL REFERENCES "Turno"(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    status driver_shift_reservation_status NOT NULL DEFAULT 'REQUESTED',
    note TEXT,
    "decidedAt" TIMESTAMP WITH TIME ZONE,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_driver_shift_reservation UNIQUE (driver_id, turno_id, date)
);

CREATE INDEX IF NOT EXISTS idx_driver_shift_reservation_driver
ON "DriverShiftReservation"(operator_id, driver_id, date, status);

CREATE TABLE IF NOT EXISTS "DriverDevice" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    "deviceIdentifier" VARCHAR(255) NOT NULL,
    platform VARCHAR(30) NOT NULL,
    label VARCHAR(120) NOT NULL,
    status driver_device_status NOT NULL DEFAULT 'ACTIVE',
    trusted BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    "lastSeenAt" TIMESTAMP WITH TIME ZONE,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_driver_device_identifier UNIQUE (driver_id, "deviceIdentifier")
);

CREATE INDEX IF NOT EXISTS idx_driver_device_driver
ON "DriverDevice"(operator_id, driver_id, status, "lastSeenAt" DESC);

CREATE TABLE IF NOT EXISTS "DriverDeviceSecurityEvent" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    device_id UUID NOT NULL REFERENCES "DriverDevice"(id) ON DELETE CASCADE,
    "riskLevel" driver_security_risk_level NOT NULL,
    flags JSONB NOT NULL DEFAULT '{}'::jsonb,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_driver_security_event_driver
ON "DriverDeviceSecurityEvent"(operator_id, driver_id, "createdAt" DESC);

CREATE TABLE IF NOT EXISTS "DriverOfflineSyncBatch" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    "deviceIdentifier" VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    "itemCount" INT NOT NULL DEFAULT 0,
    status offline_sync_status NOT NULL DEFAULT 'RECEIVED',
    "failReason" TEXT,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_driver_offline_sync_driver
ON "DriverOfflineSyncBatch"(operator_id, driver_id, status, "createdAt" DESC);

CREATE TABLE IF NOT EXISTS "DriverExpense" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    order_id UUID REFERENCES "Order"(id) ON DELETE SET NULL,
    type driver_expense_type NOT NULL,
    "amountCents" BIGINT NOT NULL,
    description TEXT NOT NULL,
    status driver_expense_status NOT NULL DEFAULT 'SUBMITTED',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT check_driver_expense_amount CHECK ("amountCents" > 0)
);

CREATE INDEX IF NOT EXISTS idx_driver_expense_driver
ON "DriverExpense"(operator_id, driver_id, status, "createdAt" DESC);

CREATE TABLE IF NOT EXISTS "DriverExpenseReceipt" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    expense_id UUID NOT NULL REFERENCES "DriverExpense"(id) ON DELETE CASCADE,
    "fileUrl" TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_driver_expense_receipt_expense
ON "DriverExpenseReceipt"(operator_id, expense_id, "createdAt" DESC);

ALTER TABLE "DriverShiftReservation" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "DriverDevice" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "DriverDeviceSecurityEvent" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "DriverOfflineSyncBatch" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "DriverExpense" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "DriverExpenseReceipt" ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    BEGIN
        CREATE POLICY "Isolamento de Tenant - DriverShiftReservation" ON "DriverShiftReservation"
        AS PERMISSIVE FOR ALL
        USING (is_platform_admin() OR operator_id = current_operator_id());
    EXCEPTION WHEN duplicate_object THEN NULL;
    END;

    BEGIN
        CREATE POLICY "Isolamento de Tenant - DriverDevice" ON "DriverDevice"
        AS PERMISSIVE FOR ALL
        USING (is_platform_admin() OR operator_id = current_operator_id());
    EXCEPTION WHEN duplicate_object THEN NULL;
    END;

    BEGIN
        CREATE POLICY "Isolamento de Tenant - DriverDeviceSecurityEvent" ON "DriverDeviceSecurityEvent"
        AS PERMISSIVE FOR ALL
        USING (is_platform_admin() OR operator_id = current_operator_id());
    EXCEPTION WHEN duplicate_object THEN NULL;
    END;

    BEGIN
        CREATE POLICY "Isolamento de Tenant - DriverOfflineSyncBatch" ON "DriverOfflineSyncBatch"
        AS PERMISSIVE FOR ALL
        USING (is_platform_admin() OR operator_id = current_operator_id());
    EXCEPTION WHEN duplicate_object THEN NULL;
    END;

    BEGIN
        CREATE POLICY "Isolamento de Tenant - DriverExpense" ON "DriverExpense"
        AS PERMISSIVE FOR ALL
        USING (is_platform_admin() OR operator_id = current_operator_id());
    EXCEPTION WHEN duplicate_object THEN NULL;
    END;

    BEGIN
        CREATE POLICY "Isolamento de Tenant - DriverExpenseReceipt" ON "DriverExpenseReceipt"
        AS PERMISSIVE FOR ALL
        USING (is_platform_admin() OR operator_id = current_operator_id());
    EXCEPTION WHEN duplicate_object THEN NULL;
    END;
END $$;
