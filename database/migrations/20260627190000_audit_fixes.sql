-- Migration: Audit Fixes (Nivel S3 Omega Swarm)
-- Creates missing tables for the 'todos' app, fixes missing columns, and ensures RLS policies are complete.

-- 1. Fix missing column in Operator
ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS cnpj VARCHAR(14) NULL;

-- 2. Create missing Todo tables
CREATE TABLE IF NOT EXISTS "TodoCategory" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    color VARCHAR(20) DEFAULT '#3B82F6' NOT NULL
);

CREATE TABLE IF NOT EXISTS "Todo" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT NULL,
    category_id UUID NULL REFERENCES "TodoCategory"(id) ON DELETE SET NULL,
    priority VARCHAR(20) DEFAULT 'MEDIUM' NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDING' NOT NULL,
    due_date TIMESTAMP WITH TIME ZONE NULL,
    "completedAt" TIMESTAMP WITH TIME ZONE NULL,
    created_by_id UUID NOT NULL REFERENCES "StaffMember"(id) ON DELETE RESTRICT,
    related_store_id UUID NULL REFERENCES "Store"(id) ON DELETE CASCADE,
    related_client_id UUID NULL REFERENCES "Client"(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "TodoAssignment" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    operator_id UUID NOT NULL REFERENCES "Operator"(id) ON DELETE CASCADE,
    todo_id UUID NOT NULL REFERENCES "Todo"(id) ON DELETE CASCADE,
    assigned_to_staff_id UUID NULL REFERENCES "StaffMember"(id) ON DELETE CASCADE,
    assigned_to_driver_id UUID NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    assigned_by_id UUID NOT NULL REFERENCES "StaffMember"(id) ON DELETE RESTRICT,
    CONSTRAINT todo_assignment_single_assignee CHECK ((assigned_to_staff_id IS NOT NULL) <> (assigned_to_driver_id IS NOT NULL))
);

-- 3. Enable RLS
ALTER TABLE "TodoCategory" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "Todo" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "TodoAssignment" ENABLE ROW LEVEL SECURITY;

-- 4. Add RLS Policies for Todo
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Isolamento de Tenant - TodoCategory') THEN
        CREATE POLICY "Isolamento de Tenant - TodoCategory" ON "TodoCategory" AS PERMISSIVE FOR ALL USING (is_platform_admin() OR operator_id = current_operator_id());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Isolamento de Tenant - Todo') THEN
        CREATE POLICY "Isolamento de Tenant - Todo" ON "Todo" AS PERMISSIVE FOR ALL USING (is_platform_admin() OR operator_id = current_operator_id());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Isolamento de Tenant - TodoAssignment') THEN
        CREATE POLICY "Isolamento de Tenant - TodoAssignment" ON "TodoAssignment" AS PERMISSIVE FOR ALL USING (is_platform_admin() OR operator_id = current_operator_id());
    END IF;
END $$;

-- 5. Add MISSING RLS Policies for Operator and PlatformAdmin
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Isolamento de Tenant - Operator') THEN
        CREATE POLICY "Isolamento de Tenant - Operator" ON "Operator" AS PERMISSIVE FOR ALL USING (is_platform_admin() OR id = current_operator_id());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Isolamento de Tenant - PlatformAdmin') THEN
        CREATE POLICY "Isolamento de Tenant - PlatformAdmin" ON "PlatformAdmin" AS PERMISSIVE FOR ALL USING (is_platform_admin());
    END IF;
END $$;
