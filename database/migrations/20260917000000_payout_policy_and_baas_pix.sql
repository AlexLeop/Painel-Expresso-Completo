-- Migração: Sistema de Política de Saque e BaaS Pix (Efí Pay / Banco Central)
-- Cria tabela PayoutPolicyConfig e expande WithdrawalRequest e Contract

-- 1. Criação da tabela PayoutPolicyConfig
CREATE TABLE IF NOT EXISTS "PayoutPolicyConfig" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    mode VARCHAR(30) NOT NULL DEFAULT 'HYBRID_THRESHOLD',
    "autoThresholdCents" BIGINT NOT NULL DEFAULT 15000,
    "dailyLimitPerDriverCents" BIGINT NOT NULL DEFAULT 50000,
    "minWithdrawalCents" BIGINT NOT NULL DEFAULT 1000,
    "payoutFeeMode" VARCHAR(30) NOT NULL DEFAULT 'ABSORBED_BY_PLATFORM',
    "payoutFeeCents" BIGINT NOT NULL DEFAULT 0,
    "notifyPushEnabled" BOOLEAN NOT NULL DEFAULT TRUE,
    "notifyWhatsappEnabled" BOOLEAN NOT NULL DEFAULT TRUE,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_payout_policy_operator UNIQUE (operator_id)
);

CREATE INDEX IF NOT EXISTS idx_payout_policy_operator ON "PayoutPolicyConfig"(operator_id);

-- 2. Evolução de WithdrawalRequest para suporte a BaaS PIX imediato, alçadas e tarifas
ALTER TABLE "WithdrawalRequest"
    ADD COLUMN IF NOT EXISTS "pixKeyType" VARCHAR(20) NOT NULL DEFAULT 'CPF',
    ADD COLUMN IF NOT EXISTS "approvalMode" VARCHAR(30) NOT NULL DEFAULT 'AUTO_INSTANT',
    ADD COLUMN IF NOT EXISTS "feeAmountCents" BIGINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS "netAmountCents" BIGINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS approved_by_id UUID NULL REFERENCES "StaffMember"(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS "approvedAt" TIMESTAMP WITH TIME ZONE NULL,
    ADD COLUMN IF NOT EXISTS "rejectionReason" TEXT NULL,
    ADD COLUMN IF NOT EXISTS "baasProvider" VARCHAR(50) NOT NULL DEFAULT 'EFI_PAY',
    ADD COLUMN IF NOT EXISTS "baasTransactionId" VARCHAR(255) NULL,
    ADD COLUMN IF NOT EXISTS "baasRawResponse" JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS "failureReason" TEXT NULL,
    ADD COLUMN IF NOT EXISTS "processedAt" TIMESTAMP WITH TIME ZONE NULL;

CREATE INDEX IF NOT EXISTS idx_withdrawal_status ON "WithdrawalRequest"(operator_id, status);
CREATE INDEX IF NOT EXISTS idx_withdrawal_processed_at ON "WithdrawalRequest"(operator_id, "processedAt");

-- 3. Evolução de Contract para sobreposições de política por cliente/loja
ALTER TABLE "Contract"
    ADD COLUMN IF NOT EXISTS "overridePayoutPolicy" BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS "customPayoutMode" VARCHAR(30) NULL,
    ADD COLUMN IF NOT EXISTS "customAutoThresholdCents" BIGINT NULL,
    ADD COLUMN IF NOT EXISTS "customFeeMode" VARCHAR(30) NULL,
    ADD COLUMN IF NOT EXISTS "customFeeCents" BIGINT NULL;
