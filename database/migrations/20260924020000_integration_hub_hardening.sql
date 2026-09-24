-- F-04: idempotência concorrente, tenant fail-closed e catálogo honesto.

DO $$
BEGIN
    IF EXISTS (
        SELECT integration_id, raw_payload_hash
        FROM integration_webhook_log
        GROUP BY integration_id, raw_payload_hash
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'F-04: existem logs de webhook duplicados; consolide-os antes do deploy';
    END IF;

    IF EXISTS (
        SELECT operator_id, store_id, external_source, external_order_id
        FROM "Order"
        WHERE external_source IS NOT NULL AND external_order_id IS NOT NULL
        GROUP BY operator_id, store_id, external_source, external_order_id
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'F-04: existem pedidos externos duplicados; consolide-os antes do deploy';
    END IF;
END $$;

DROP INDEX IF EXISTS idx_webhook_log_dedup;
CREATE UNIQUE INDEX IF NOT EXISTS uq_webhook_log_dedup
    ON integration_webhook_log (integration_id, raw_payload_hash);

CREATE UNIQUE INDEX IF NOT EXISTS uq_order_external_per_store
    ON "Order" (operator_id, store_id, external_source, external_order_id)
    WHERE external_source IS NOT NULL AND external_order_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_store_connector_integration
    ON "StoreIntegration" (operator_id, store_id, connector_id)
    WHERE connector_id IS NOT NULL;

DROP POLICY IF EXISTS integration_webhook_log_tenant_policy ON integration_webhook_log;
CREATE POLICY integration_webhook_log_tenant_policy ON integration_webhook_log
    AS PERMISSIVE FOR ALL
    USING (
        is_platform_admin() OR EXISTS (
            SELECT 1
            FROM "StoreIntegration" si
            WHERE si.id = integration_webhook_log.integration_id
              AND si.operator_id = current_operator_id()
        )
    )
    WITH CHECK (
        is_platform_admin() OR EXISTS (
            SELECT 1
            FROM "StoreIntegration" si
            WHERE si.id = integration_webhook_log.integration_id
              AND si.operator_id = current_operator_id()
        )
    );

UPDATE integration_connector
SET status = 'disabled', "updatedAt" = now()
WHERE slug <> 'generic-webhook';

UPDATE integration_connector
SET config_schema = '{
  "type": "object",
  "properties": {
    "default_delivery_fee_cents": {
      "type": "integer",
      "minimum": 0,
      "maximum": 10000000
    },
    "notification_email": {"type": "string", "maxLength": 254}
  },
  "additionalProperties": false
}'::jsonb,
status = 'active',
"updatedAt" = now()
WHERE slug = 'generic-webhook';
