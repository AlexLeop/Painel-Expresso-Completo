-- Client portal access must be revocable without destroying audit references.
ALTER TABLE "ClientPortalUser"
    ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE;

CREATE INDEX IF NOT EXISTS idx_client_portal_user_active
    ON "ClientPortalUser" (operator_id, active);
