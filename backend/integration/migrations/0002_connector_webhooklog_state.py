"""Register integration hub models in Django state without database DDL.

The physical tables are owned by the canonical SQL migration runner.
"""

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("integration", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="IntegrationConnector",
                    fields=[
                        (
                            "id",
                            models.UUIDField(
                                default=uuid.uuid4,
                                editable=False,
                                primary_key=True,
                                serialize=False,
                            ),
                        ),
                        ("slug", models.CharField(max_length=50, unique=True)),
                        ("name", models.CharField(max_length=100)),
                        ("description", models.TextField(blank=True, null=True)),
                        (
                            "icon_url",
                            models.CharField(blank=True, max_length=500, null=True),
                        ),
                        (
                            "auth_type",
                            models.CharField(
                                default="webhook_signature",
                                help_text=(
                                    "Tipo de autenticação: oauth2, api_key, "
                                    "webhook_signature, mtls, none"
                                ),
                                max_length=30,
                            ),
                        ),
                        (
                            "config_schema",
                            models.JSONField(blank=True, default=dict),
                        ),
                        (
                            "webhook_path_template",
                            models.CharField(max_length=200),
                        ),
                        (
                            "capabilities",
                            models.JSONField(blank=True, default=list),
                        ),
                        (
                            "status",
                            models.CharField(
                                default="active",
                                help_text=(
                                    "Status: active, beta, deprecated, disabled"
                                ),
                                max_length=20,
                            ),
                        ),
                        (
                            "documentation_url",
                            models.CharField(blank=True, max_length=500, null=True),
                        ),
                        (
                            "version",
                            models.CharField(default="1.0.0", max_length=20),
                        ),
                        (
                            "createdAt",
                            models.DateTimeField(
                                auto_now_add=True, db_column="createdAt"
                            ),
                        ),
                        (
                            "updatedAt",
                            models.DateTimeField(
                                auto_now=True, db_column="updatedAt"
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "Conector de Integração",
                        "verbose_name_plural": "Conectores de Integração",
                        "db_table": "integration_connector",
                        "managed": False,
                    },
                ),
                migrations.CreateModel(
                    name="IntegrationWebhookLog",
                    fields=[
                        (
                            "id",
                            models.UUIDField(
                                default=uuid.uuid4,
                                editable=False,
                                primary_key=True,
                                serialize=False,
                            ),
                        ),
                        (
                            "connector_slug",
                            models.CharField(
                                db_column="connector_slug", max_length=50
                            ),
                        ),
                        (
                            "raw_payload_hash",
                            models.CharField(
                                db_column="raw_payload_hash", max_length=64
                            ),
                        ),
                        (
                            "status",
                            models.CharField(
                                choices=[
                                    ("received", "Received"),
                                    ("processed", "Processed"),
                                    ("failed", "Failed"),
                                    ("duplicate", "Duplicate"),
                                    ("rejected", "Rejected"),
                                ],
                                db_column="status",
                                default="received",
                                max_length=20,
                            ),
                        ),
                        (
                            "order_id",
                            models.UUIDField(
                                blank=True, db_column="order_id", null=True
                            ),
                        ),
                        (
                            "error_detail",
                            models.TextField(
                                blank=True, db_column="error_detail", null=True
                            ),
                        ),
                        (
                            "processing_ms",
                            models.IntegerField(
                                blank=True, db_column="processing_ms", null=True
                            ),
                        ),
                        (
                            "createdAt",
                            models.DateTimeField(
                                auto_now_add=True, db_column="createdAt"
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "Log de Webhook de Integração",
                        "verbose_name_plural": "Logs de Webhook de Integração",
                        "db_table": "integration_webhook_log",
                        "ordering": ["-createdAt"],
                        "managed": False,
                    },
                ),
            ],
        ),
    ]
