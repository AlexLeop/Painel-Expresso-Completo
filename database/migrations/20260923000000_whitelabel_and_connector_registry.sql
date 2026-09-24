-- ================================================================
-- Migration: White-Label Branding + Integration Connector Registry
-- Part of: WL-001 + HUB-INT-001
-- Date: 2026-09-23
-- ================================================================

-- ----------------------------------------------------------------
-- 1. Add slug column to Operator for white-label URL identification
-- ----------------------------------------------------------------
ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS slug VARCHAR(100);

-- Backfill existing operators with slug derived from name
UPDATE "Operator"
SET slug = left(trim(both '-' from lower(regexp_replace(name, '[^a-zA-Z0-9]+', '-', 'g'))), 80)
           || '-' || left(id::text, 8)
WHERE slug IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_operator_slug ON "Operator" (slug);

-- ----------------------------------------------------------------
-- 2. Create operator_branding table (1:1 with Operator)
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS operator_branding (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    operator_id UUID NOT NULL UNIQUE REFERENCES "Operator"(id) ON DELETE CASCADE,

    -- Identidade
    brand_name VARCHAR(255) NOT NULL,

    -- Assets
    logo_url VARCHAR(500),
    favicon_url VARCHAR(500),

    -- Paleta Light Mode
    color_primary VARCHAR(7) NOT NULL DEFAULT '#6366f1',
    color_secondary VARCHAR(7) NOT NULL DEFAULT '#4f46e5',
    color_accent VARCHAR(7) NOT NULL DEFAULT '#f59e0b',
    color_background VARCHAR(7) NOT NULL DEFAULT '#ffffff',
    color_surface VARCHAR(7) NOT NULL DEFAULT '#f4f4f5',
    color_text VARCHAR(7) NOT NULL DEFAULT '#18181b',

    -- Paleta Dark Mode
    dark_color_background VARCHAR(7) NOT NULL DEFAULT '#0a0a0a',
    dark_color_surface VARCHAR(7) NOT NULL DEFAULT '#171717',
    dark_color_text VARCHAR(7) NOT NULL DEFAULT '#fafafa',

    -- Preferência de tema
    theme_mode VARCHAR(10) NOT NULL DEFAULT 'light'
        CHECK (theme_mode IN ('light', 'dark', 'auto')),

    -- Timestamps
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
    "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS
ALTER TABLE operator_branding ENABLE ROW LEVEL SECURITY;

-- Branding visual é público para leitura (necessário para tela de login customizada por subdomínio/slug)
CREATE POLICY operator_branding_public_select ON operator_branding
    FOR SELECT USING (true);

CREATE POLICY operator_branding_tenant_insert ON operator_branding
    FOR INSERT WITH CHECK (is_platform_admin() OR operator_id = current_operator_id());

CREATE POLICY operator_branding_tenant_update ON operator_branding
    FOR UPDATE USING (is_platform_admin() OR operator_id = current_operator_id())
    WITH CHECK (is_platform_admin() OR operator_id = current_operator_id());

CREATE POLICY operator_branding_tenant_delete ON operator_branding
    FOR DELETE USING (is_platform_admin() OR operator_id = current_operator_id());

CREATE INDEX IF NOT EXISTS idx_operator_branding_operator ON operator_branding(operator_id);

-- Backfill: create default branding for existing operators
INSERT INTO operator_branding (operator_id, brand_name)
SELECT id, name FROM "Operator"
ON CONFLICT (operator_id) DO NOTHING;

-- ----------------------------------------------------------------
-- 3. Create integration_connector registry (shared, NOT tenant-scoped)
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS integration_connector (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon_url VARCHAR(500),
    auth_type VARCHAR(30) NOT NULL DEFAULT 'webhook_signature'
        CHECK (auth_type IN ('oauth2', 'api_key', 'webhook_signature', 'mtls', 'none')),
    config_schema JSONB NOT NULL DEFAULT '{}',
    webhook_path_template VARCHAR(200) NOT NULL,
    capabilities JSONB NOT NULL DEFAULT '["receive_orders"]',
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'beta', 'deprecated', 'disabled')),
    documentation_url VARCHAR(500),
    version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
    "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- No RLS on integration_connector — it's a shared global registry.

-- Seed default connectors
INSERT INTO integration_connector (slug, name, description, auth_type, webhook_path_template, capabilities, status) VALUES
    ('generic-webhook', 'Webhook Genérico',
     'Conecte qualquer sistema próprio enviando webhooks no formato padronizado. Autenticação via HMAC-SHA256.',
     'webhook_signature',
     '/api/v1/integration/webhooks/generic-webhook/{integration_id}',
     '["receive_orders"]', 'active'),
    ('ifood', 'iFood',
     'Integração oficial com o iFood para receber pedidos e atualizar status de entrega.',
     'oauth2',
     '/api/v1/integration/webhooks/ifood/{integration_id}',
     '["receive_orders", "update_status"]', 'disabled'),
    ('delivery-direto', 'Delivery Direto',
     'Receba pedidos do Delivery Direto automaticamente via webhook.',
     'api_key',
     '/api/v1/integration/webhooks/delivery-direto/{integration_id}',
     '["receive_orders"]', 'disabled'),
    ('anota-ai', 'Anota AI',
     'Integração com a Anota AI para receber pedidos de cardápio digital.',
     'oauth2',
     '/api/v1/integration/webhooks/anota-ai/{integration_id}',
     '["receive_orders"]', 'disabled'),
    ('saipos', 'Saipos',
     'Receba pedidos do sistema Saipos PDV automaticamente.',
     'api_key',
     '/api/v1/integration/webhooks/saipos/{integration_id}',
     '["receive_orders"]', 'disabled'),
    ('neemo', 'Neemo',
     'Integração com a plataforma Neemo para delivery digital.',
     'api_key',
     '/api/v1/integration/webhooks/neemo/{integration_id}',
     '["receive_orders"]', 'disabled'),
    ('goomer', 'Goomer',
     'Receba pedidos do cardápio digital Goomer.',
     'api_key',
     '/api/v1/integration/webhooks/goomer/{integration_id}',
     '["receive_orders"]', 'disabled'),
    ('aiqfome', 'aiqfome',
     'Integração com o app de delivery aiqfome.',
     'api_key',
     '/api/v1/integration/webhooks/aiqfome/{integration_id}',
     '["receive_orders"]', 'disabled'),
    ('rappi', 'Rappi',
     'Receba pedidos da plataforma Rappi via integração de parceiro logístico.',
     'oauth2',
     '/api/v1/integration/webhooks/rappi/{integration_id}',
     '["receive_orders", "update_status"]', 'disabled'),
    ('consumer-grandchef', 'Consumer / GrandChef',
     'Integração com os sistemas Consumer e GrandChef para automação de delivery.',
     'api_key',
     '/api/v1/integration/webhooks/consumer-grandchef/{integration_id}',
     '["receive_orders"]', 'disabled')
ON CONFLICT (slug) DO NOTHING;

-- ----------------------------------------------------------------
-- 4. Add connector_id FK to existing StoreIntegration
-- ----------------------------------------------------------------
ALTER TABLE "StoreIntegration"
    ADD COLUMN IF NOT EXISTS connector_id UUID REFERENCES integration_connector(id),
    ADD COLUMN IF NOT EXISTS webhook_secret TEXT,
    ADD COLUMN IF NOT EXISTS config JSONB NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS auto_create_order BOOLEAN NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS last_webhook_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS error_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS error_message TEXT;

-- ----------------------------------------------------------------
-- 5. Create integration_webhook_log for dedup + audit
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS integration_webhook_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    integration_id UUID NOT NULL REFERENCES "StoreIntegration"(id) ON DELETE CASCADE,
    connector_slug VARCHAR(50) NOT NULL,
    raw_payload_hash VARCHAR(64) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'received'
        CHECK (status IN ('received', 'processed', 'failed', 'duplicate', 'rejected')),
    order_id UUID,
    error_detail TEXT,
    processing_ms INTEGER,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS via integration FK chain
ALTER TABLE integration_webhook_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY integration_webhook_log_tenant_policy ON integration_webhook_log
    AS PERMISSIVE FOR ALL
    USING (
        is_platform_admin() OR
        EXISTS (
            SELECT 1 FROM "StoreIntegration" si
            WHERE si.id = integration_webhook_log.integration_id
              AND si.operator_id = current_operator_id()
        )
    );

-- Dedup index
CREATE UNIQUE INDEX IF NOT EXISTS uq_webhook_log_dedup
    ON integration_webhook_log(integration_id, raw_payload_hash);

-- Listing index
CREATE INDEX IF NOT EXISTS idx_webhook_log_listing
    ON integration_webhook_log(integration_id, "createdAt" DESC);

-- ================================================================
-- END
-- ================================================================
