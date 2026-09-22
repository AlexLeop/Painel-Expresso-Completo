-- ============================================================================
-- DRIVER ENTERPRISE P0
-- Status operacional, sessão de turno, incidentes e metadados de proof
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'driver_operational_status') THEN
        CREATE TYPE driver_operational_status AS ENUM (
            'ONLINE',
            'OFFLINE',
            'PAUSED',
            'EN_ROUTE',
            'IN_SERVICE',
            'RESTING'
        );
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'driver_shift_session_status') THEN
        CREATE TYPE driver_shift_session_status AS ENUM (
            'OPEN',
            'CLOSED'
        );
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'proof_stage') THEN
        CREATE TYPE proof_stage AS ENUM (
            'PICKUP',
            'DELIVERY'
        );
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'driver_incident_type') THEN
        CREATE TYPE driver_incident_type AS ENUM (
            'CLIENTE_AUSENTE',
            'ENDERECO_INCORRETO',
            'RECUSA',
            'PRODUTO_DANIFICADO',
            'ACIDENTE',
            'ROUBO',
            'EXTRAVIO',
            'OUTRO'
        );
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'driver_incident_status') THEN
        CREATE TYPE driver_incident_status AS ENUM (
            'OPEN',
            'RESOLVED',
            'CANCELED'
        );
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'driver_attachment_type') THEN
        CREATE TYPE driver_attachment_type AS ENUM (
            'PHOTO',
            'VIDEO',
            'AUDIO',
            'DOCUMENT'
        );
    END IF;
END $$;

ALTER TABLE "Driver"
ADD COLUMN IF NOT EXISTS operational_status driver_operational_status NOT NULL DEFAULT 'OFFLINE';

ALTER TABLE "Proof"
ADD COLUMN IF NOT EXISTS stage proof_stage NOT NULL DEFAULT 'DELIVERY',
ADD COLUMN IF NOT EXISTS geom GEOGRAPHY(Point, 4326),
ADD COLUMN IF NOT EXISTS "gpsAccuracyMeters" INT,
ADD COLUMN IF NOT EXISTS "deviceIdentifier" VARCHAR(255),
ADD COLUMN IF NOT EXISTS "confirmationCode" VARCHAR(100),
ADD COLUMN IF NOT EXISTS "qrCode" VARCHAR(255),
ADD COLUMN IF NOT EXISTS barcode TEXT,
ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_proof_geom ON "Proof" USING GIST(geom);

CREATE TABLE IF NOT EXISTS "DriverStatusAudit" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    previous_status driver_operational_status NOT NULL,
    new_status driver_operational_status NOT NULL,
    reason TEXT,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_driver_status_audit_driver_time
ON "DriverStatusAudit"(operator_id, driver_id, "createdAt" DESC);

CREATE TABLE IF NOT EXISTS "DriverShiftSession" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    "scheduleEntryId" UUID REFERENCES "ScheduleEntry"(id) ON DELETE SET NULL,
    status driver_shift_session_status NOT NULL DEFAULT 'OPEN',
    "checkInAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    "checkOutAt" TIMESTAMP WITH TIME ZONE,
    reason TEXT,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_driver_shift_session_driver
ON "DriverShiftSession"(operator_id, driver_id, status, "checkInAt" DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_driver_shift_session_open
ON "DriverShiftSession"(driver_id)
WHERE status = 'OPEN';

CREATE TABLE IF NOT EXISTS "DriverIncident" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    order_id UUID REFERENCES "Order"(id) ON DELETE SET NULL,
    stop_id UUID REFERENCES "Stop"(id) ON DELETE SET NULL,
    type driver_incident_type NOT NULL,
    status driver_incident_status NOT NULL DEFAULT 'OPEN',
    description TEXT NOT NULL,
    geom GEOGRAPHY(Point, 4326),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    "resolvedAt" TIMESTAMP WITH TIME ZONE,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_driver_incident_driver
ON "DriverIncident"(operator_id, driver_id, status, "createdAt" DESC);

CREATE INDEX IF NOT EXISTS idx_driver_incident_geom
ON "DriverIncident" USING GIST(geom);

CREATE TABLE IF NOT EXISTS "DriverIncidentAttachment" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    incident_id UUID NOT NULL REFERENCES "DriverIncident"(id) ON DELETE CASCADE,
    type driver_attachment_type NOT NULL,
    "fileUrl" TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_driver_incident_attachment_incident
ON "DriverIncidentAttachment"(operator_id, incident_id, "createdAt" DESC);

ALTER TABLE "DriverStatusAudit" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "DriverShiftSession" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "DriverIncident" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "DriverIncidentAttachment" ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    BEGIN
        CREATE POLICY "Isolamento de Tenant - DriverStatusAudit" ON "DriverStatusAudit"
        AS PERMISSIVE FOR ALL
        USING (is_platform_admin() OR operator_id = current_operator_id());
    EXCEPTION WHEN duplicate_object THEN
        NULL;
    END;

    BEGIN
        CREATE POLICY "Isolamento de Tenant - DriverShiftSession" ON "DriverShiftSession"
        AS PERMISSIVE FOR ALL
        USING (is_platform_admin() OR operator_id = current_operator_id());
    EXCEPTION WHEN duplicate_object THEN
        NULL;
    END;

    BEGIN
        CREATE POLICY "Isolamento de Tenant - DriverIncident" ON "DriverIncident"
        AS PERMISSIVE FOR ALL
        USING (is_platform_admin() OR operator_id = current_operator_id());
    EXCEPTION WHEN duplicate_object THEN
        NULL;
    END;

    BEGIN
        CREATE POLICY "Isolamento de Tenant - DriverIncidentAttachment" ON "DriverIncidentAttachment"
        AS PERMISSIVE FOR ALL
        USING (is_platform_admin() OR operator_id = current_operator_id());
    EXCEPTION WHEN duplicate_object THEN
        NULL;
    END;
END $$;
