from django.db import migrations, connection


def add_operator_billing_columns(apps, schema_editor):
    if connection.vendor == "postgresql":
        schema_editor.execute("""
            ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS phone VARCHAR(50);
            ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS city VARCHAR(100);
            ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS state VARCHAR(10);
            ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS "billingPlanType" VARCHAR(50) DEFAULT 'PERCENT_PER_DELIVERY';
            ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS "billingRateValue" NUMERIC(10,2) DEFAULT 0.00;
            ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS "billingCycle" VARCHAR(30) DEFAULT 'MENSAL';
            ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS "dueDay" INTEGER DEFAULT 10;
            ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS "trialDays" INTEGER DEFAULT 14;
            ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS "gracePeriodDays" INTEGER DEFAULT 5;
            ALTER TABLE "Operator" ADD COLUMN IF NOT EXISTS notes TEXT;
        """)


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.RunPython(add_operator_billing_columns, migrations.RunPython.noop),
    ]
