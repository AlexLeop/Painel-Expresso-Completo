-- Migração de Prontidão de Produção: Forçar RLS e Idempotência Contábil
-- 1. Forçar RLS inclusive para o proprietário da tabela (impede bypass silencioso do Django / table owner)
DO $$
DECLARE
    tbl text;
    tables text[] := ARRAY[
        'Order', 'Stop', 'Driver', 'Store', 'Position', 
        'Wallet', 'WalletTransaction', 'WeeklyStoreInvoice', 
        'WeeklyInvoiceLineItem', 'ManualEntry'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables LOOP
        IF EXISTS (
            SELECT 1 FROM pg_tables 
            WHERE schemaname = 'public' AND tablename = tbl
        ) THEN
            EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY;', tbl);
        END IF;
    END LOOP;
END $$;

-- 2. Idempotência estrita no Ledger Financeiro:
-- Uma corrida só pode gerar uma transação de carteira de mesma categoria por operador
CREATE UNIQUE INDEX IF NOT EXISTS idx_wallet_tx_order_category_unique
    ON "WalletTransaction" (operator_id, category, (metadata->>'order_id'))
    WHERE metadata->>'order_id' IS NOT NULL;

-- 3. Uma corrida só pode constar uma única vez em uma fatura semanal de estabelecimento
CREATE UNIQUE INDEX IF NOT EXISTS idx_weekly_invoice_order_unique
    ON "WeeklyInvoiceLineItem" (order_id);
