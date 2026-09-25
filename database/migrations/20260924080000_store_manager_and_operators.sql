-- Migration: 20260924080000_store_manager_and_operators.sql
-- Adds role support to ClientPortalUser to distinguish between:
-- 1) 'lojista' (Gestor da Loja / Dono do Estabelecimento)
-- 2) 'operador_loja' (Funcionário da Loja / Operador do Delivery)

ALTER TABLE "ClientPortalUser"
    ADD COLUMN IF NOT EXISTS role VARCHAR(50) NOT NULL DEFAULT 'lojista';

CREATE INDEX IF NOT EXISTS idx_client_portal_user_role
    ON "ClientPortalUser" (operator_id, client_id, role);
