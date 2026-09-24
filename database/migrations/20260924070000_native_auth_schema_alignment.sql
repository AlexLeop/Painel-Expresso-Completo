-- Align the SQL-owned schema with the native-auth Django models.
-- These columns are nullable so existing Supabase-linked identities remain valid
-- until an explicit password is set through the management commands/APIs.

ALTER TABLE "PlatformAdmin"
    ADD COLUMN IF NOT EXISTS "passwordHash" VARCHAR(255);

ALTER TABLE "StaffMember"
    ADD COLUMN IF NOT EXISTS "passwordHash" VARCHAR(255);

ALTER TABLE "ClientPortalUser"
    ADD COLUMN IF NOT EXISTS "passwordHash" VARCHAR(255);

ALTER TABLE "Driver"
    ADD COLUMN IF NOT EXISTS "passwordHash" VARCHAR(255);

-- Native identities may be created without a legacy Supabase identifier.
ALTER TABLE "PlatformAdmin"
    ALTER COLUMN supabase_uid DROP NOT NULL;

ALTER TABLE "StaffMember"
    ALTER COLUMN supabase_uid DROP NOT NULL;

ALTER TABLE "Driver"
    ALTER COLUMN supabase_uid DROP NOT NULL;
