"""Register OperatorBranding in Django's migration state without database DDL.

The physical table is owned by the canonical SQL migration runner.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_ensure_roles_and_operator_saas"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="OperatorBranding",
                    fields=[
                        (
                            "id",
                            models.UUIDField(
                                editable=False, primary_key=True, serialize=False
                            ),
                        ),
                        (
                            "brand_name",
                            models.CharField(
                                help_text=(
                                    "Nome visível no login, sidebar e relatórios "
                                    "(substitui 'Expresso Neves')."
                                ),
                                max_length=255,
                            ),
                        ),
                        (
                            "logo_url",
                            models.CharField(
                                blank=True,
                                help_text="URL do logo (armazenado via upload endpoint).",
                                max_length=500,
                                null=True,
                            ),
                        ),
                        (
                            "favicon_url",
                            models.CharField(
                                blank=True,
                                help_text="URL do favicon (armazenado via upload endpoint).",
                                max_length=500,
                                null=True,
                            ),
                        ),
                        (
                            "color_primary",
                            models.CharField(
                                default="#6366f1",
                                help_text=(
                                    "Cor primária (hex #RRGGBB) — botões, links, header."
                                ),
                                max_length=7,
                            ),
                        ),
                        (
                            "color_secondary",
                            models.CharField(
                                default="#4f46e5",
                                help_text=(
                                    "Cor secundária (hex #RRGGBB) — sidebar, destaques."
                                ),
                                max_length=7,
                            ),
                        ),
                        (
                            "color_accent",
                            models.CharField(
                                default="#f59e0b",
                                help_text=(
                                    "Cor de acento (hex #RRGGBB) — badges, CTAs."
                                ),
                                max_length=7,
                            ),
                        ),
                        (
                            "color_background",
                            models.CharField(
                                default="#ffffff",
                                help_text="Fundo principal (light mode).",
                                max_length=7,
                            ),
                        ),
                        (
                            "color_surface",
                            models.CharField(
                                default="#f4f4f5",
                                help_text=(
                                    "Superfície de cards e painéis (light mode)."
                                ),
                                max_length=7,
                            ),
                        ),
                        (
                            "color_text",
                            models.CharField(
                                default="#18181b",
                                help_text="Cor de texto principal (light mode).",
                                max_length=7,
                            ),
                        ),
                        (
                            "dark_color_background",
                            models.CharField(
                                default="#0a0a0a",
                                help_text="Fundo principal (dark mode).",
                                max_length=7,
                            ),
                        ),
                        (
                            "dark_color_surface",
                            models.CharField(
                                default="#171717",
                                help_text="Superfície de cards (dark mode).",
                                max_length=7,
                            ),
                        ),
                        (
                            "dark_color_text",
                            models.CharField(
                                default="#fafafa",
                                help_text="Texto principal (dark mode).",
                                max_length=7,
                            ),
                        ),
                        (
                            "theme_mode",
                            models.CharField(
                                default="light",
                                help_text="Modo do tema: light, dark, auto.",
                                max_length=10,
                            ),
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
                        "verbose_name": "Branding do Operador",
                        "verbose_name_plural": "Brandings dos Operadores",
                        "db_table": "operator_branding",
                        "managed": False,
                    },
                ),
            ],
        ),
    ]
