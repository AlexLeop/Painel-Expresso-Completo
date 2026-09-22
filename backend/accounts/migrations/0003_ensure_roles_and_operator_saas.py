from django.db import migrations, connection


def ensure_postgres_roles_and_columns(apps, schema_editor):
    if connection.vendor == "postgresql":
        schema_editor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    CREATE ROLE anon NOLOGIN;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    CREATE ROLE authenticated NOLOGIN;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
                    CREATE ROLE service_role NOLOGIN;
                END IF;
            END $$;

            GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
            GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated, service_role;
            GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated, service_role;

            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO authenticated, service_role;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO authenticated, service_role;

            GRANT anon TO CURRENT_USER;
            GRANT authenticated TO CURRENT_USER;
            GRANT service_role TO CURRENT_USER;

            ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS "platformCostPerDeliveryCents" INTEGER DEFAULT 40;
            ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS "platformMinMonthlyFloorCents" INTEGER DEFAULT 29900;
            ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS "platformVolumeTiers" JSONB DEFAULT '[]'::jsonb;
        """)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_initial'),
    ]

    operations = [
        migrations.RunPython(ensure_postgres_roles_and_columns, migrations.RunPython.noop),
    ]
