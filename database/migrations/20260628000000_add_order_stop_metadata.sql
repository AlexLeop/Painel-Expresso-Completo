-- Adiciona coluna metadata JSONB nativa para armazenar dados flexíveis como endereço e contato
-- Isso permite a migração transparente dos dados da Taxi Machine sem inflar o schema fixo.

ALTER TABLE "Order" ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;
ALTER TABLE "Stop" ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- Criação de índices GIN para permitir busca rápida dentro do JSON, caso necessário no futuro
CREATE INDEX IF NOT EXISTS idx_order_metadata ON "Order" USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_stop_metadata ON "Stop" USING GIN(metadata);
