"""
Modelos de White-Label (Branding) para Operadores Logísticos.

Permite que cada operador personalize a aparência do painel com logo,
cores, favicon e nome de marca. Relação 1:1 com Operator.

managed = False: O banco de dados é a fonte da verdade (Supabase CLI / migrations SQL).
"""

import uuid
from django.db import models
from accounts.models import Operator


class OperatorBranding(models.Model):
    """
    Personalização de marca (white-label) por operador logístico.

    Armazena toda a configuração visual que permite aos operadores
    apresentar o painel com a identidade da sua própria empresa para
    seus clientes (lojistas). Cada operador tem no máximo um registro.
    """

    id = models.UUIDField(primary_key=True, editable=False)
    operator = models.OneToOneField(
        Operator,
        on_delete=models.CASCADE,
        db_column="operator_id",
        related_name="branding",
    )
    operator_id: uuid.UUID

    # Identidade
    brand_name = models.CharField(
        max_length=255,
        help_text="Nome visível no login, sidebar e relatórios (substitui 'Expresso Neves').",
    )

    # Assets
    logo_url = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="URL do logo (armazenado via upload endpoint).",
    )
    favicon_url = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="URL do favicon (armazenado via upload endpoint).",
    )

    # Paleta Light Mode
    color_primary = models.CharField(
        max_length=7,
        default="#6366f1",
        help_text="Cor primária (hex #RRGGBB) — botões, links, header.",
    )
    color_secondary = models.CharField(
        max_length=7,
        default="#4f46e5",
        help_text="Cor secundária (hex #RRGGBB) — sidebar, destaques.",
    )
    color_accent = models.CharField(
        max_length=7,
        default="#f59e0b",
        help_text="Cor de acento (hex #RRGGBB) — badges, CTAs.",
    )
    color_background = models.CharField(
        max_length=7,
        default="#ffffff",
        help_text="Fundo principal (light mode).",
    )
    color_surface = models.CharField(
        max_length=7,
        default="#f4f4f5",
        help_text="Superfície de cards e painéis (light mode).",
    )
    color_text = models.CharField(
        max_length=7,
        default="#18181b",
        help_text="Cor de texto principal (light mode).",
    )

    # Paleta Dark Mode
    dark_color_background = models.CharField(
        max_length=7,
        default="#0a0a0a",
        help_text="Fundo principal (dark mode).",
    )
    dark_color_surface = models.CharField(
        max_length=7,
        default="#171717",
        help_text="Superfície de cards (dark mode).",
    )
    dark_color_text = models.CharField(
        max_length=7,
        default="#fafafa",
        help_text="Texto principal (dark mode).",
    )

    # Preferência de tema
    theme_mode = models.CharField(
        max_length=10,
        default="light",
        help_text="Modo do tema: light, dark, auto.",
    )

    # Timestamps
    createdAt = models.DateTimeField(auto_now_add=True, db_column="createdAt")
    updatedAt = models.DateTimeField(auto_now=True, db_column="updatedAt")

    class Meta:
        db_table = "operator_branding"
        managed = False
        verbose_name = "Branding do Operador"
        verbose_name_plural = "Brandings dos Operadores"

    def __str__(self):
        return f"Branding: {self.brand_name} ({self.operator_id})"
