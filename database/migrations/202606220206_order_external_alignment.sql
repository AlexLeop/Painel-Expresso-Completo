ALTER TABLE "Order"
ADD COLUMN IF NOT EXISTS external_order_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS external_source VARCHAR(50);

CREATE UNIQUE INDEX IF NOT EXISTS idx_order_external
ON "Order"(store_id, external_source, external_order_id);
