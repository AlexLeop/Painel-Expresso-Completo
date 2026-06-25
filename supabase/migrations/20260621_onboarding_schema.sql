-- ============================================================================
-- MIGRAÇÃO DE ONBOARDING E NOVOS FLUXOS LOGIPAY
-- Adiciona tax_classification, onboarding_status, e constraints corporativas
-- ============================================================================

-- 1. Criação dos novos ENUMs
CREATE TYPE driver_onboarding_status AS ENUM (
    'INVITED',           -- cadastrado pelo staff, app não acessado ainda
    'PENDING_DOCUMENTS', -- logou no app, documentos não enviados
    'UNDER_REVIEW',      -- documentos enviados, aguardando revisão do staff
    'APPROVED',          -- todos os docs válidos, pode ser escalado
    'BLOCKED'            -- bloqueado por documento vencido ou deny-list
);

CREATE TYPE driver_tax_classification AS ENUM (
    'PESSOA_FISICA_AUTONOMO',
    'MEI'
);

CREATE TYPE driver_document_type AS ENUM (
    'CNH',
    'PROOF_OF_ADDRESS',
    'VEHICLE_DOCUMENT',
    'MEI_CERTIFICATE'
);

-- 2. Alteração na tabela Driver (Adicionar onboarding e tax class)
ALTER TABLE "Driver"
ADD COLUMN onboarding_status driver_onboarding_status NOT NULL DEFAULT 'INVITED',
ADD COLUMN tax_classification driver_tax_classification NOT NULL DEFAULT 'PESSOA_FISICA_AUTONOMO',
ADD COLUMN document VARCHAR(20); -- CNPJ ou CPF para validar fiscalmente

-- 3. Tabela de Requisitos de Documentos por Classificação
CREATE TABLE "DriverDocumentRequirement" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tax_class driver_tax_classification NOT NULL,
    document_type driver_document_type NOT NULL,
    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (tax_class, document_type)
);
-- Aplicando RLS para a tabela de configuração global (Leitura publica para tenant ou global)
ALTER TABLE "DriverDocumentRequirement" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "DriverDocumentRequirement_Select" ON "DriverDocumentRequirement" FOR SELECT USING (true);

-- Seeds
INSERT INTO "DriverDocumentRequirement" (tax_class, document_type, is_required) VALUES
  ('PESSOA_FISICA_AUTONOMO', 'CNH', true),
  ('PESSOA_FISICA_AUTONOMO', 'PROOF_OF_ADDRESS', true),
  ('PESSOA_FISICA_AUTONOMO', 'VEHICLE_DOCUMENT', false),
  ('MEI', 'CNH', true),
  ('MEI', 'MEI_CERTIFICATE', true),
  ('MEI', 'PROOF_OF_ADDRESS', true),
  ('MEI', 'VEHICLE_DOCUMENT', false);

-- 4. Tabela DriverDocument existente (adicionar status e enum apropriado se necessário)
-- A tabela original não tinha type nem status!
ALTER TABLE "DriverDocument"
ADD COLUMN document_type driver_document_type NOT NULL DEFAULT 'CNH',
ADD COLUMN status entry_status NOT NULL DEFAULT 'PENDING_APPROVAL',
ADD COLUMN "rejectReason" TEXT;

-- 5. Alteração na tabela Contract
ALTER TABLE "Contract"
ADD COLUMN effective_from DATE NOT NULL DEFAULT CURRENT_DATE;

-- 6. Alteração na tabela Store
ALTER TABLE "Store"
ADD COLUMN operational BOOLEAN NOT NULL DEFAULT FALSE;
