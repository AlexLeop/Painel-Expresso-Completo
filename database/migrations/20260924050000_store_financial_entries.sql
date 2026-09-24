-- Store-only balance adjustments must not invent or impersonate a driver.
ALTER TABLE "ManualEntry"
    ALTER COLUMN driver_id DROP NOT NULL;

ALTER TABLE "ManualEntry"
    ADD CONSTRAINT manual_entry_has_counterparty
    CHECK (driver_id IS NOT NULL OR store_id IS NOT NULL) NOT VALID;

ALTER TABLE "ManualEntry" VALIDATE CONSTRAINT manual_entry_has_counterparty;
