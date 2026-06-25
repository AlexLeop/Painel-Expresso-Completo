-- ============================================================================
-- BANCO DE DADOS LOGÍSTICO MULTI-TENANT (SUPABASE POSTGRESQL + POSTGIS)
-- Autores: Arquiteto de Banco de Dados Sênior & Equipe de Engenharia
-- Versão: 2.1 (Revisada com Partições, Métricas de BigInt e Geografia Projetada)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 0. EXTENSÕES DO POSTGRESQL
-- ----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- ----------------------------------------------------------------------------
-- 1. ENUMS OPERACIONAIS E FINANCEIROS
-- ----------------------------------------------------------------------------
CREATE TYPE role_type AS ENUM ('ADMIN', 'MANAGER', 'OPERATOR_ROLE', 'VIEWER');
CREATE TYPE vehicle_type AS ENUM ('MOTORCYCLE', 'BICYCLE', 'CAR');
CREATE TYPE proof_type AS ENUM ('PHOTO', 'SIGNATURE', 'SCAN');
CREATE TYPE stop_type AS ENUM ('PICKUP', 'DROPOFF', 'RETURN');
CREATE TYPE geofence_event_type AS ENUM ('ENTER', 'EXIT');

CREATE TYPE order_status AS ENUM (
    'PREPARING', 
    'READY_FOR_DISPATCH', 
    'OFFERED', 
    'ACCEPTED', 
    'STARTED', 
    'ARRIVED', 
    'COMPLETED', 
    'CANCELED', 
    'CANCELED_IN_TRANSIT', 
    'RETURNING_TO_STORE', 
    'RETURNED'
);

CREATE TYPE manifest_status AS ENUM ('OPEN', 'LOCKED', 'COMPLETED', 'CANCELED');
CREATE TYPE manifest_grouping_method AS ENUM ('MANUAL', 'AUTOMATIC');


CREATE TYPE entry_status AS ENUM ('PENDING_APPROVAL', 'APPROVED', 'REJECTED');
CREATE TYPE tax_category AS ENUM ('TAXABLE_INCOME', 'NON_TAXABLE_REIMBURSEMENT', 'DEDUCTION');

CREATE TYPE wallet_transaction_category AS ENUM (
    'DAILY_SETTLEMENT', 
    'ADVANCE', 
    'PAYOUT', 
    'ADJUSTMENT', 
    'BONUS', 
    'PENALTY', 
    'RETURN_RIDE', 
    'REFUND'
);

CREATE TYPE daily_credit_status AS ENUM ('PENDING', 'CREDITED', 'SKIPPED', 'FAILED');
CREATE TYPE invoice_status AS ENUM ('DRAFT', 'DISPUTED', 'FINALIZED', 'LOCKED', 'PAID');
CREATE TYPE invoice_item_status AS ENUM ('ACTIVE', 'DISPUTED', 'WAIVED');
CREATE TYPE withdrawal_status AS ENUM ('PENDING', 'PROCESSING', 'PAID', 'FAILED');

CREATE TYPE operator_status AS ENUM ('TRIAL', 'ACTIVE', 'SUSPENDED', 'CANCELED');

-- ----------------------------------------------------------------------------
-- 2. TABELA MASTER DE TENANTS
-- ----------------------------------------------------------------------------
CREATE TABLE "Operator" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    status operator_status NOT NULL DEFAULT 'TRIAL',
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE "Operator" IS 'Tabela Master dos Tenants (Operadores Logísticos). Isolamento físico/lógico principal.';

-- ----------------------------------------------------------------------------
-- 3. TABELAS DE CADASTRO E CORE (RLS ENABLED)
-- ----------------------------------------------------------------------------
CREATE TABLE "PlatformAdmin" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    supabase_uid UUID UNIQUE NOT NULL, -- Necessário para match com is_platform_admin() no JWT
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE "OperatorAuditLog" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    "platformAdminId" UUID NOT NULL REFERENCES "PlatformAdmin"(id) ON DELETE RESTRICT,
    action VARCHAR(100) NOT NULL, -- CREATED, SUSPENDED, PLAN_CHANGED
    "previousStatus" operator_status,
    "newStatus" operator_status,
    reason TEXT NOT NULL,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_operator_audit ON "OperatorAuditLog"(operator_id, "createdAt" DESC);

CREATE TABLE "StaffMember" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    supabase_uid UUID UNIQUE NOT NULL, -- Link estrito com o Supabase Auth externo
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    role role_type NOT NULL DEFAULT 'OPERATOR_ROLE',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
-- Índice multi-tenant otimizado contendo operator_id na frente
CREATE INDEX idx_staff_operator ON "StaffMember"(operator_id, active);

CREATE TABLE "SecurityDenylist" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    "targetId" UUID NOT NULL, -- ID do Driver ou Staff bloqueado
    "targetType" VARCHAR(50) NOT NULL, -- 'DRIVER' ou 'STAFF'
    reason TEXT NOT NULL,
    "blockedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "expiresAt" TIMESTAMP WITH TIME ZONE -- NULL significa banimento permanente
);
CREATE INDEX idx_security_denylist_target ON "SecurityDenylist"(operator_id, "targetId", "expiresAt");
COMMENT ON TABLE "SecurityDenylist" IS 'Fonte de verdade para a Deny-list do Redis. Previne perda da lista negra caso o Redis reinicie e serve de auditoria forense.';

CREATE TABLE "Client" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    document VARCHAR(20) NOT NULL, -- CPF ou CNPJ
    active BOOLEAN NOT NULL DEFAULT TRUE,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_client_operator ON "Client"(operator_id, active);

CREATE TABLE "ClientPortalUser" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES "Client"(id) ON DELETE CASCADE,
    supabase_uid UUID UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_client_user_client ON "ClientPortalUser"(operator_id, client_id);

CREATE TABLE "Store" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES "Client"(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    "averagePrepTimeMinutes" INT NOT NULL DEFAULT 15, -- Prep-time sync control
    latitude DOUBLE PRECISION GENERATED ALWAYS AS (ST_Y(geom::geometry)) STORED,
    longitude DOUBLE PRECISION GENERATED ALWAYS AS (ST_X(geom::geometry)) STORED,
    geom GEOGRAPHY(Point, 4326) NOT NULL, -- Alterado para Geography para cálculos nativos em metros
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_store_operator ON "Store"(operator_id, client_id);
CREATE INDEX idx_store_geom ON "Store" USING GIST(geom); -- Spatial index for geofencing/routing

CREATE TABLE "Turno" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    store_id UUID NOT NULL REFERENCES "Store"(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    "startTime" TIME NOT NULL,
    "endTime" TIME NOT NULL
);
CREATE INDEX idx_turno_store ON "Turno"(operator_id, store_id);

CREATE TABLE "Vehicle" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    plate VARCHAR(10) UNIQUE NOT NULL,
    type vehicle_type NOT NULL DEFAULT 'MOTORCYCLE',
    active BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX idx_vehicle_operator ON "Vehicle"(operator_id, active);

CREATE TABLE "Driver" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    supabase_uid UUID UNIQUE NOT NULL, -- Link estrito com o Supabase Auth externo
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    "pixKeyType" VARCHAR(20) NOT NULL,
    "pixKey" VARCHAR(255) NOT NULL,
    online BOOLEAN NOT NULL DEFAULT FALSE,
    latitude DOUBLE PRECISION GENERATED ALWAYS AS (ST_Y(geom::geometry)) STORED,
    longitude DOUBLE PRECISION GENERATED ALWAYS AS (ST_X(geom::geometry)) STORED,
    geom GEOGRAPHY(Point, 4326), -- Live telemetry geography
    heading INT DEFAULT 0, -- Rotação no mapa (graus)
    "speedKmh" INT DEFAULT 0, -- Telemetria ao vivo
    "lastPingAt" TIMESTAMP WITH TIME ZONE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_driver_operator ON "Driver"(operator_id, online, active);
CREATE INDEX idx_driver_geom ON "Driver" USING GIST(geom); -- Spatial Index for live location matching

CREATE TABLE "StoreDriver" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    store_id UUID NOT NULL REFERENCES "Store"(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_store_driver UNIQUE (store_id, driver_id)
);
CREATE INDEX idx_storedriver_store ON "StoreDriver"(operator_id, store_id);
CREATE INDEX idx_storedriver_driver ON "StoreDriver"(operator_id, driver_id);

CREATE TABLE "Place" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    street VARCHAR(255) NOT NULL,
    number VARCHAR(20),
    neighborhood VARCHAR(100),
    city VARCHAR(100) NOT NULL,
    "postalCode" VARCHAR(15) NOT NULL,
    "accessCode" VARCHAR(50), -- Código de portão ou bloco
    latitude DOUBLE PRECISION GENERATED ALWAYS AS (ST_Y(geom::geometry)) STORED,
    longitude DOUBLE PRECISION GENERATED ALWAYS AS (ST_X(geom::geometry)) STORED,
    geom GEOGRAPHY(Point, 4326) NOT NULL
);
CREATE INDEX idx_place_geom ON "Place" USING GIST(geom);

-- ----------------------------------------------------------------------------
-- 4. TABELAS DE ESCALA, DISPATCH E TELEMETRIA
-- ----------------------------------------------------------------------------
CREATE TABLE "ServiceZone" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    geom GEOGRAPHY(Polygon, 4326) NOT NULL, -- PostGIS Geography Polygon para tarifas de risco calculadas em metros
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_servicezone_operator ON "ServiceZone"(operator_id);
CREATE INDEX idx_servicezone_geom ON "ServiceZone" USING GIST(geom); -- GIST Index para cruzamento de polígonos

CREATE TABLE "ScheduleEntry" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    store_id UUID NOT NULL REFERENCES "Store"(id) ON DELETE CASCADE,
    turno_id UUID NOT NULL REFERENCES "Turno"(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    "minGuaranteedOverrideCents" INT, -- Piso diário customizado para escala específica
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_driver_date_shift UNIQUE (driver_id, date, turno_id)
);
CREATE INDEX idx_schedule_entry_search ON "ScheduleEntry"(operator_id, store_id, date, turno_id);
COMMENT ON TABLE "ScheduleEntry" IS 'Tabela que trava o Ring-Fencing contábil/operacional. Vincula o entregador à escala da loja no dia.';

CREATE TABLE "ScheduleEntryAudit" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    "scheduleEntryId" UUID NOT NULL REFERENCES "ScheduleEntry"(id) ON DELETE CASCADE,
    "staffId" UUID NOT NULL REFERENCES "StaffMember"(id) ON DELETE RESTRICT,
    "previousStoreId" UUID REFERENCES "Store"(id) ON DELETE SET NULL,
    "newStoreId" UUID REFERENCES "Store"(id) ON DELETE SET NULL,
    reason TEXT NOT NULL,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE "Manifest" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    driver_id UUID REFERENCES "Driver"(id) ON DELETE SET NULL,
    status manifest_status NOT NULL DEFAULT 'OPEN',
    "groupingMethod" manifest_grouping_method NOT NULL DEFAULT 'AUTOMATIC',
    "totalDistanceMeters" INT NOT NULL DEFAULT 0,
    "totalEtaSeconds" INT NOT NULL DEFAULT 0,
    "lockedAt" TIMESTAMP WITH TIME ZONE,
    "completedAt" TIMESTAMP WITH TIME ZONE,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_manifest_driver ON "Manifest"(operator_id, driver_id, status);

CREATE TABLE "Order" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    store_id UUID NOT NULL REFERENCES "Store"(id) ON DELETE CASCADE,
    driver_id UUID REFERENCES "Driver"(id) ON DELETE SET NULL,
    manifest_id UUID REFERENCES "Manifest"(id) ON DELETE SET NULL,
    status VARCHAR(30) DEFAULT 'PREPARING',
    "fareValueCents" BIGINT NOT NULL,
    "storeAuthorizedBonusCents" BIGINT DEFAULT 0,
    "distanceMeters" INTEGER NOT NULL,
    "businessDate" DATE NOT NULL,
    "allocationDifficulty" BOOLEAN DEFAULT FALSE,
    "requestedAt" TIMESTAMPTZ DEFAULT NOW(),
    "acceptedAt" TIMESTAMPTZ,
    "startedAt" TIMESTAMPTZ,
    "arrivedAt" TIMESTAMPTZ,
    "completedAt" TIMESTAMPTZ,
    "canceledAt" TIMESTAMPTZ,
    external_order_id VARCHAR(255),
    external_source VARCHAR(50),
    CONSTRAINT check_bonus_positive CHECK ("storeAuthorizedBonusCents" >= 0),
    CONSTRAINT check_fare_positive CHECK ("fareValueCents" >= 0)
);
CREATE UNIQUE INDEX idx_order_external ON "Order"(store_id, external_source, external_order_id);
CREATE INDEX idx_order_business_date ON "Order"(operator_id, store_id, "businessDate");
CREATE INDEX idx_order_status ON "Order"(operator_id, status);
CREATE INDEX idx_order_manifest ON "Order"(operator_id, manifest_id);
COMMENT ON COLUMN "Order"."businessDate" IS 'Competência financeira. Gerada a partir dos parâmetros de corte do contrato da loja no momento da criação.';

CREATE TABLE "Stop" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    order_id UUID NOT NULL REFERENCES "Order"(id) ON DELETE CASCADE,
    sequence INT NOT NULL,
    type stop_type NOT NULL DEFAULT 'DROPOFF',
    latitude DOUBLE PRECISION GENERATED ALWAYS AS (ST_Y(geom::geometry)) STORED,
    longitude DOUBLE PRECISION GENERATED ALWAYS AS (ST_X(geom::geometry)) STORED,
    geom GEOGRAPHY(Point, 4326) NOT NULL, -- Ponto PostGIS de Geografia da parada
    "requiresPin" BOOLEAN NOT NULL DEFAULT FALSE,
    "deliveryPinHash" TEXT, -- bcrypt do PIN, NULL = PIN não exigido
    "completedAt" TIMESTAMP WITH TIME ZONE
);
CREATE INDEX idx_stop_order ON "Stop"(operator_id, order_id);
CREATE INDEX idx_stop_geom ON "Stop" USING GIST(geom); -- Spatial Index para geofence auto-arrival

CREATE TABLE "ManifestStop" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    manifest_id UUID NOT NULL REFERENCES "Manifest"(id) ON DELETE CASCADE,
    stop_id UUID NOT NULL REFERENCES "Stop"(id) ON DELETE CASCADE,
    sequence INT NOT NULL,
    CONSTRAINT unique_manifest_stop UNIQUE (manifest_id, stop_id)
);
CREATE INDEX idx_manifeststop_manifest ON "ManifestStop"(operator_id, manifest_id);

-- ----------------------------------------------------------------------------
-- 4.1. TABELA DE TELEMETRIA PARTICIADA (POSITION)
-- ----------------------------------------------------------------------------
CREATE TABLE "Position" (
    id UUID NOT NULL,
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    latitude DOUBLE PRECISION GENERATED ALWAYS AS (ST_Y(geom::geometry)) STORED,
    longitude DOUBLE PRECISION GENERATED ALWAYS AS (ST_X(geom::geometry)) STORED,
    geom GEOGRAPHY(Point, 4326) NOT NULL, -- Telemetria com geografia nativa em metros
    heading INT NOT NULL,
    "speedKmh" INT NOT NULL,
    "capturedAt" TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id, "capturedAt") -- capturedAt obrigatório na PK para suporte à partição declarativa
) PARTITION BY RANGE ("capturedAt");

CREATE TABLE "Position_default" PARTITION OF "Position" DEFAULT;

CREATE INDEX idx_position_driver_time ON "Position"(operator_id, driver_id, "capturedAt" DESC);
CREATE INDEX idx_position_geom ON "Position" USING GIST(geom);
COMMENT ON TABLE "Position" IS 'Tabela com histórico de telemetria particionada por mês. Otimização física para trilhões de pings.';

CREATE TABLE "Proof" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    stop_id UUID NOT NULL REFERENCES "Stop"(id) ON DELETE CASCADE,
    type proof_type NOT NULL DEFAULT 'PHOTO',
    "fileUrl" TEXT NOT NULL,
    "capturedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_proof_stop ON "Proof"(operator_id, stop_id);

CREATE TABLE "GeofenceEvent" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    stop_id UUID NOT NULL REFERENCES "Stop"(id) ON DELETE CASCADE,
    type geofence_event_type NOT NULL,
    "capturedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_geofence_stop ON "GeofenceEvent"(operator_id, stop_id);

-- ----------------------------------------------------------------------------
-- 5. TABELAS DO MOTOR FINANCEIRO E CARTEIRA (CONTRATOS E LEDGER COM BIGINT)
-- ----------------------------------------------------------------------------
CREATE TYPE compensation_mode AS ENUM ('PRODUCAO', 'GARANTIDA', 'GARANTIDA_HORAS');

CREATE TABLE "Contract" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    store_id UUID UNIQUE NOT NULL REFERENCES "Store"(id) ON DELETE CASCADE,
    "compensationMode" compensation_mode NOT NULL DEFAULT 'GARANTIDA',
    "rideFeePerDeliveryCents" INT NOT NULL, -- Valor pago ao entregador por parada
    "minimumRidesFeeFloorCents" INT NOT NULL, -- Mínimo garantido caso o volume seja baixo
    "minimumFloorBps" INT NOT NULL, -- Percentual de repasse do piso (Basis Points: 10000 = 100%)
    "adminTaxThresholdCents" INT NOT NULL, -- Teto administrativo
    "adminTaxFixedAmountCents" INT NOT NULL, -- Valor de taxa administrativa fixa
    "adminTaxBps" INT NOT NULL, -- Porcentagem da taxa administrativa (Basis Points)
    "supervisionFeePerWeekCents" INT NOT NULL DEFAULT 0, -- Taxa semanal de supervisão
    "dailyRateWeekdayCents" INT NOT NULL DEFAULT 0, -- Diária fixa de segunda a sexta
    "dailyRateSaturdayCents" INT NOT NULL DEFAULT 0,
    "dailyRateSundayCents" INT NOT NULL DEFAULT 0,
    "dailyRateHolidayCents" INT NOT NULL DEFAULT 0,
    "kmExcedenteValorCents" INT NOT NULL DEFAULT 0, -- Valor por KM rodado excedente
    "allowAutomaticGrouping" BOOLEAN NOT NULL DEFAULT TRUE,
    "cloudOverflowAllowed" BOOLEAN NOT NULL DEFAULT FALSE, -- Chave de liberação de transbordo de escala para Nuvem
    "maxStopsPerManifest" INT NOT NULL DEFAULT 3,
    "maxDetourPercent" INT NOT NULL DEFAULT 20,
    "cutoffHour" INT NOT NULL DEFAULT 2, -- Corte diário (ex: 2h da manhã)
    "cutoffMinute" INT NOT NULL DEFAULT 0,
    "returnFeeBps" INT NOT NULL DEFAULT 5000, -- Taxa de devolução em BPS (ex: 5000 = 50%)
    CONSTRAINT check_cutoff_hour CHECK ("cutoffHour" BETWEEN 0 AND 23),
    CONSTRAINT check_cutoff_minute CHECK ("cutoffMinute" BETWEEN 0 AND 59)
);

CREATE TABLE "KmFaixa" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    contract_id UUID NOT NULL REFERENCES "Contract"(id) ON DELETE CASCADE,
    "kmStart" INT NOT NULL,
    "kmEnd" INT NOT NULL,
    "priceCents" INT NOT NULL,
    CONSTRAINT check_km_range_order CHECK ("kmStart" < "kmEnd")
);

CREATE TABLE "FaixaHoras" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    contract_id UUID NOT NULL REFERENCES "Contract"(id) ON DELETE CASCADE,
    "hoursMin" NUMERIC(4,2) NOT NULL,
    "hoursMax" NUMERIC(4,2) NOT NULL,
    "priceCents" INT NOT NULL,
    CONSTRAINT check_faixa_hours_order CHECK ("hoursMin" < "hoursMax")
);

CREATE TABLE "Wallet" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    driver_id UUID UNIQUE NOT NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    "balanceCents" BIGINT NOT NULL DEFAULT 0, -- Alterado para BIGINT para segurança em larga escala
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_wallet_operator UNIQUE (operator_id, id)
);
COMMENT ON TABLE "Wallet" IS 'Carteira do entregador. O saldo é um valor cacheado, auditado e atualizado atomicamente.';

CREATE TABLE "OperatorInternalWallet" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID UNIQUE NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    "balanceCents" BIGINT NOT NULL DEFAULT 0, -- Alterado para BIGINT para evitar overflow no caixa total da empresa
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_operator_wallet_operator UNIQUE (operator_id, id)
);
COMMENT ON TABLE "OperatorInternalWallet" IS 'Conta corporativa do Operador. Utilizada para contrapartida contábil de bônus/multas privadas.';

CREATE TABLE "WalletTransaction" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    
    -- Origem do dinheiro
    source_driver_wallet_id UUID,
    source_operator_wallet_id UUID,
    FOREIGN KEY (operator_id, source_driver_wallet_id) REFERENCES "Wallet"(operator_id, id) ON DELETE CASCADE,
    FOREIGN KEY (operator_id, source_operator_wallet_id) REFERENCES "OperatorInternalWallet"(operator_id, id) ON DELETE CASCADE,
    
    -- Destino do dinheiro
    destination_driver_wallet_id UUID,
    destination_operator_wallet_id UUID,
    FOREIGN KEY (operator_id, destination_driver_wallet_id) REFERENCES "Wallet"(operator_id, id) ON DELETE CASCADE,
    FOREIGN KEY (operator_id, destination_operator_wallet_id) REFERENCES "OperatorInternalWallet"(operator_id, id) ON DELETE CASCADE,
    
    "amountCents" BIGINT NOT NULL, -- Valores estritamente positivos, direção dada pelas contas
    category wallet_transaction_category NOT NULL,
    "taxCategory" tax_category NOT NULL, -- Natureza da rubrica para RPA/MEI
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT check_transaction_amount CHECK ("amountCents" > 0),
    CONSTRAINT check_source_xor CHECK (num_nonnulls(source_driver_wallet_id, source_operator_wallet_id) = 1),
    CONSTRAINT check_dest_xor CHECK (num_nonnulls(destination_driver_wallet_id, destination_operator_wallet_id) = 1),
    CONSTRAINT check_not_same_driver CHECK (source_driver_wallet_id IS NULL OR destination_driver_wallet_id IS NULL OR source_driver_wallet_id <> destination_driver_wallet_id),
    CONSTRAINT check_not_same_operator CHECK (source_operator_wallet_id IS NULL OR destination_operator_wallet_id IS NULL OR source_operator_wallet_id <> destination_operator_wallet_id)
);
CREATE INDEX idx_tx_src_driver ON "WalletTransaction"(operator_id, source_driver_wallet_id);
CREATE INDEX idx_tx_dest_driver ON "WalletTransaction"(operator_id, destination_driver_wallet_id);
CREATE INDEX idx_tx_src_operator ON "WalletTransaction"(operator_id, source_operator_wallet_id);
CREATE INDEX idx_tx_dest_operator ON "WalletTransaction"(operator_id, destination_operator_wallet_id);
COMMENT ON TABLE "WalletTransaction" IS 'Ledger Imutável (Partidas Dobradas). Todos os fluxos financeiros são registrados com Origem e Destino com isolamento transacional de Tenant.';

CREATE TABLE "ManualEntry" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    store_id UUID REFERENCES "Store"(id) ON DELETE SET NULL, -- Nullable (pode ser um lançamento privado da operadora)
    
    "created_by_staff_id" UUID REFERENCES "StaffMember"(id) ON DELETE RESTRICT,
    "created_by_client_id" UUID REFERENCES "ClientPortalUser"(id) ON DELETE RESTRICT,
    
    "amountCents" BIGINT NOT NULL, -- Alterado para BIGINT para conciliação estrita com Wallet
    description TEXT NOT NULL,
    "visibleToStore" BOOLEAN NOT NULL DEFAULT TRUE, -- Visibilidade da cobrança para a loja B2B
    "taxCategory" tax_category NOT NULL,
    status entry_status NOT NULL DEFAULT 'PENDING_APPROVAL', -- Trava contra fraude (Maker-Checker)
    "rejectReason" TEXT,
    "approvedById" UUID REFERENCES "StaffMember"(id) ON DELETE RESTRICT, -- Apenas Manager ou Admin
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT check_manual_amount CHECK ("amountCents" <> 0),
    CONSTRAINT check_creator_xor CHECK (num_nonnulls("created_by_staff_id", "created_by_client_id") = 1)
);
CREATE INDEX idx_manual_entry_approval ON "ManualEntry"(operator_id, status);

CREATE TABLE "DailyCreditCalculation" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    store_id UUID NOT NULL REFERENCES "Store"(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    status daily_credit_status NOT NULL DEFAULT 'PENDING',
    "productionValueCents" BIGINT NOT NULL DEFAULT 0,
    "extrasCents" BIGINT NOT NULL DEFAULT 0,
    "dailyRateOrGuaranteedCents" BIGINT NOT NULL DEFAULT 0,
    "advancesCents" BIGINT NOT NULL DEFAULT 0,
    "netAmountCents" BIGINT NOT NULL DEFAULT 0,
    "failReason" TEXT,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_driver_store_date_calc UNIQUE (driver_id, store_id, date)
);
CREATE INDEX idx_daily_calc ON "DailyCreditCalculation"(operator_id, driver_id, date);

CREATE TABLE "WeeklyStoreInvoice" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    store_id UUID NOT NULL REFERENCES "Store"(id) ON DELETE CASCADE,
    "startDate" DATE NOT NULL,
    "endDate" DATE NOT NULL,
    
    -- Breakdown Financeiro
    "totalNetProducaoCents" BIGINT NOT NULL DEFAULT 0,
    "totalNetGarantidaCents" BIGINT NOT NULL DEFAULT 0,
    "administrativeFeeCents" BIGINT NOT NULL DEFAULT 0,
    "supervisionFeeCents" BIGINT NOT NULL DEFAULT 0,
    "pendingDebitCarriedCents" BIGINT NOT NULL DEFAULT 0,
    
    -- O Celery calcula e grava quando finaliza a fatura (não pode ser GENERATED devido à escolha XOR de garantida/producao)
    "totalCents" BIGINT NOT NULL DEFAULT 0,

    status invoice_status NOT NULL DEFAULT 'DRAFT', -- DRAFT -> DISPUTED -> FINALIZED -> LOCKED -> PAID
    "paymentGatewayId" VARCHAR(255), -- Link do Asaas
    "pixCopyPaste" TEXT,
    barcode TEXT,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_invoice_store_week UNIQUE (store_id, "startDate")
);
CREATE INDEX idx_weekly_invoice ON "WeeklyStoreInvoice"(operator_id, store_id, "startDate");

CREATE TABLE "WeeklyInvoiceLineItem" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    invoice_id UUID NOT NULL REFERENCES "WeeklyStoreInvoice"(id) ON DELETE CASCADE,
    driver_id UUID REFERENCES "Driver"(id) ON DELETE SET NULL, -- Rastreabilidade B2B
    "businessDate" DATE, -- Data do serviço (crucial para Diárias sem Order)
    order_id UUID REFERENCES "Order"(id) ON DELETE SET NULL,
    "manualEntryId" UUID REFERENCES "ManualEntry"(id) ON DELETE SET NULL,
    description TEXT NOT NULL,
    "amountCents" BIGINT NOT NULL, -- Alterado para BIGINT
    status invoice_item_status NOT NULL DEFAULT 'ACTIVE',
    "disputeReason" TEXT,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_line_item_invoice ON "WeeklyInvoiceLineItem"(operator_id, invoice_id);

CREATE TABLE "WithdrawalRequest" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    "amountCents" BIGINT NOT NULL, -- Alterado para BIGINT
    status withdrawal_status NOT NULL DEFAULT 'PENDING',
    "pixKey" VARCHAR(255) NOT NULL,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT check_withdrawal_amount CHECK ("amountCents" > 0)
);
CREATE INDEX idx_withdrawal_driver ON "WithdrawalRequest"(operator_id, driver_id);

-- TRIGGER DE SEGURANÇA: Bloqueio físico contra a Fissura do Celery
CREATE OR REPLACE FUNCTION block_withdrawal_if_denylisted()
RETURNS TRIGGER AS $$
DECLARE
    is_blocked BOOLEAN;
BEGIN
    -- Verifica se o driver está ativo
    IF NOT EXISTS (SELECT 1 FROM "Driver" WHERE id = NEW.driver_id AND active = TRUE) THEN
        RAISE EXCEPTION 'Driver is inactive. Cannot process WithdrawalRequest.';
    END IF;

    -- Verifica se o driver está na Deny-list ativa
    SELECT EXISTS (
        SELECT 1 FROM "SecurityDenylist" 
        WHERE "targetId" = NEW.driver_id 
          AND "targetType" = 'DRIVER' 
          AND ("expiresAt" IS NULL OR "expiresAt" > NOW())
    ) INTO is_blocked;

    IF is_blocked THEN
        RAISE EXCEPTION 'Driver is on the Security Deny-list. Cannot process WithdrawalRequest.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_block_withdrawal_if_denylisted
BEFORE UPDATE OF status ON "WithdrawalRequest"
FOR EACH ROW
WHEN (NEW.status IN ('PROCESSING', 'PAID'))
EXECUTE FUNCTION block_withdrawal_if_denylisted();

-- ----------------------------------------------------------------------------
-- 6. TABELAS DE RH, DP E COMPLIANCE
-- ----------------------------------------------------------------------------
CREATE TABLE "DriverDocument" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    "fileUrl" TEXT NOT NULL,
    "expiresAt" DATE,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);


CREATE TABLE "DriverPaymentReceipt" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    "referenceMonth" DATE NOT NULL, -- Mês de referência (competência)
    "fileUrl" TEXT NOT NULL, -- PDF do RPA ou NF-e
    "amountCents" BIGINT NOT NULL, -- Alterado para BIGINT
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE "DriverAbsence" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    reason TEXT NOT NULL,
    justified BOOLEAN NOT NULL DEFAULT FALSE,
    "fileUrl" TEXT, -- Atestado médico
    CONSTRAINT unique_driver_absence_date UNIQUE (driver_id, date)
);

CREATE TABLE "DriverPerformanceNote" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    "staffId" UUID NOT NULL REFERENCES "StaffMember"(id) ON DELETE RESTRICT,
    type VARCHAR(50) NOT NULL, -- ELOGIO, ADVERTENCIA, SUSPENSAO
    note TEXT NOT NULL,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 7. TABELAS DE INTEGRAÇÕES E INFRAESTRUTURA
-- ----------------------------------------------------------------------------
CREATE TABLE "StoreIntegration" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    store_id UUID NOT NULL REFERENCES "Store"(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL, -- IFOOD, DELIVERY_DIRETO, SAIPOS, etc.
    "clientId" VARCHAR(255),
    "clientSecret" TEXT, -- Deve ser criptografado na aplicação
    "merchantId" VARCHAR(100),
    "apiKey" TEXT, -- Deve ser criptografado na aplicação
    active BOOLEAN NOT NULL DEFAULT TRUE,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_store_provider UNIQUE (store_id, provider)
);

CREATE TABLE "IntegrationOutbox" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    "aggregateType" VARCHAR(100) NOT NULL, -- ORDER, MANIFEST, etc.
    "aggregateId" UUID NOT NULL,
    "sequenceNumber" BIGSERIAL UNIQUE NOT NULL, -- Evita Race Conditions na integração
    "eventType" VARCHAR(100) NOT NULL, -- ORDER_DISPATCHED, ORDER_CANCELED
    payload JSONB NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING', -- PENDING, SENT, FAILED
    "attempts" INT NOT NULL DEFAULT 0,
    "lastAttemptAt" TIMESTAMP WITH TIME ZONE,
    "failReason" TEXT,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_outbox_pending ON "IntegrationOutbox"(operator_id, status, "createdAt");

-- Fim do script DDL.

-- ----------------------------------------------------------------------------
-- 8. ROW LEVEL SECURITY (RLS) E POLÍTICAS DE ISOLAMENTO (MULTI-TENANT)
-- ----------------------------------------------------------------------------

-- Habilitar RLS em todas as tabelas dinamicamente
DO $$ 
DECLARE
    t_name text;
BEGIN
    FOR t_name IN 
        SELECT table_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' AND column_name = 'operator_id'
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY;', t_name);
    END LOOP;
END $$;

-- Função genérica para capturar o operator_id do JWT do Supabase (lido de app_metadata para segurança)
CREATE OR REPLACE FUNCTION current_operator_id() RETURNS UUID AS $$
  SELECT NULLIF(current_setting('request.jwt.claims', true)::json->'app_metadata'->>'operator_id', '')::UUID;
$$ LANGUAGE SQL STABLE;

-- Função genérica para verificar se é Platform Admin (lido de app_metadata para não conflitar com 'authenticated')
CREATE OR REPLACE FUNCTION is_platform_admin() RETURNS BOOLEAN AS $$
  SELECT (current_setting('request.jwt.claims', true)::json->'app_metadata'->>'role') = 'platform_admin';
$$ LANGUAGE SQL STABLE;

-- Aplicar a Política Padrão de Isolamento (Tenant Isolado + Admin Bypass) em massa
DO $$ 
DECLARE
    t_name text;
BEGIN
    FOR t_name IN 
        SELECT table_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' AND column_name = 'operator_id'
    LOOP
        EXECUTE format('
            CREATE POLICY "Isolamento de Tenant - %s" ON %I
            AS PERMISSIVE FOR ALL
            USING (is_platform_admin() OR operator_id = current_operator_id());
        ', t_name, t_name);
    END LOOP;
END $$;
