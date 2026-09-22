ALTER TABLE "Driver"
ADD COLUMN IF NOT EXISTS "maxActiveOrders" INT NOT NULL DEFAULT 3;

ALTER TABLE "OrderAssignmentAudit"
ADD COLUMN IF NOT EXISTS changed_by_driver_id UUID REFERENCES "Driver"(id) ON DELETE SET NULL;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'order_assignment_actor_xor'
    ) THEN
        ALTER TABLE "OrderAssignmentAudit"
        DROP CONSTRAINT order_assignment_actor_xor;
    END IF;
END $$;

ALTER TABLE "OrderAssignmentAudit"
ADD CONSTRAINT order_assignment_actor_xor
CHECK (num_nonnulls(changed_by_staff_id, changed_by_client_id, changed_by_driver_id) = 1);
