import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0004_operatorbranding_state")]

    operations = [
        migrations.CreateModel(
            name="OrderNoticeRead",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("actor_id", models.UUIDField()),
                ("order_id", models.UUIDField()),
                ("read_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "constraints": [models.UniqueConstraint(
                    fields=("actor_id", "order_id"), name="order_notice_actor_order"
                )],
            },
        ),
        migrations.CreateModel(
            name="OperatorApplication",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("company_name", models.CharField(max_length=255)),
                ("document", models.CharField(max_length=14)),
                ("email", models.EmailField(max_length=254)),
                ("phone", models.CharField(max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "constraints": [models.UniqueConstraint(
                    fields=("document", "email"), name="operator_application_identity"
                )],
            },
        ),
    ]
