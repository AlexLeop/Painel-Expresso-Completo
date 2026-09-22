"""
Módulo de Gestão de Contas, Operadores e Segurança.

Este módulo concentra o núcleo de "Tenancy" e as políticas de controle
da plataforma. Define os operadores logísticos, administradores, equipes internas
(staff) e os bloqueios de segurança (denylist).

Todos os modelos herdam de `TenantModel` ou `TimeStampedTenantModel` (exceto o próprio Operator)
e operam com `managed = False` para respeitar a soberania do banco de dados (Supabase CLI).
"""

from django.db import models
from config.core_models import TimeStampedTenantModel


class Operator(models.Model):
    """
    Tabela Master dos Tenants (Operadores Logísticos).

    O Operator representa a empresa que contrata o software (franqueado, central de motoboys).
    Todos os dados do sistema são segmentados por `operator_id` (Row Level Security).
    Por ser a raiz da arquitetura multi-tenant, este é o único modelo que não herda
    da classe base TenantModel.
    """

    class OperatorStatus(models.TextChoices):
        """Estados possíveis do ciclo de vida contratual de um Operador."""

        TRIAL = "TRIAL", "Trial"
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"
        CANCELED = "CANCELED", "Canceled"

    class BillingPlanType(models.TextChoices):
        PERCENT_PER_DELIVERY = "PERCENT_PER_DELIVERY", "Percentual por Entrega"
        PERCENT_REVENUE = "PERCENT_REVENUE", "Percentual sobre Faturamento"
        FIXED_MONTHLY = "FIXED_MONTHLY", "Fixo Mensal"
        FIXED_WEEKLY = "FIXED_WEEKLY", "Fixo Semanal"
        FIXED_PER_DELIVERY = "FIXED_PER_DELIVERY", "Fixo por Corrida"

    class BillingCycle(models.TextChoices):
        MENSAL = "MENSAL", "Mensal"
        QUINZENAL = "QUINZENAL", "Quinzenal"
        SEMANAL = "SEMANAL", "Semanal"

    id = models.UUIDField(primary_key=True, editable=False)
    name = models.CharField(
        max_length=255, help_text="Razão Social ou Nome Fantasia do Operador Logístico."
    )
    cnpj = models.CharField(
        max_length=14,
        null=True,
        blank=True,
        help_text="CNPJ da operadora para emissão de Notas e cobranças.",
    )
    phone = models.CharField(
        max_length=50, null=True, blank=True, help_text="Telefone ou WhatsApp de contato."
    )
    city = models.CharField(
        max_length=100, null=True, blank=True, help_text="Cidade sede do operador."
    )
    state = models.CharField(
        max_length=10, null=True, blank=True, help_text="UF / Estado."
    )
    billingPlanType = models.CharField(
        max_length=50,
        choices=BillingPlanType.choices,
        default=BillingPlanType.PERCENT_PER_DELIVERY,
        db_column="billingPlanType",
        help_text="Modalidade de cobrança do operador.",
    )
    billingRateValue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        db_column="billingRateValue",
        help_text="Valor fixo (R$) ou percentual (%) cobrado do operador.",
    )
    billingCycle = models.CharField(
        max_length=30,
        choices=BillingCycle.choices,
        default=BillingCycle.MENSAL,
        db_column="billingCycle",
        help_text="Ciclo de cobrança/faturamento.",
    )
    dueDay = models.IntegerField(
        default=10,
        db_column="dueDay",
        help_text="Dia de vencimento da fatura (1 a 31).",
    )
    trialDays = models.IntegerField(
        default=14,
        db_column="trialDays",
        help_text="Dias de carência/degustação gratuita.",
    )
    gracePeriodDays = models.IntegerField(
        default=5,
        db_column="gracePeriodDays",
        help_text="Dias de tolerância antes do bloqueio por inadimplência.",
    )
    platformCostPerDeliveryCents = models.IntegerField(
        default=40,
        db_column="platformCostPerDeliveryCents",
        help_text="Taxa fixa cobrada pela plataforma por entrega concluída (em centavos).",
    )
    platformMinMonthlyFloorCents = models.IntegerField(
        default=29900,
        db_column="platformMinMonthlyFloorCents",
        help_text="Piso mínimo mensal garantido cobrado pela plataforma (em centavos).",
    )
    platformVolumeTiers = models.JSONField(
        null=True,
        blank=True,
        db_column="platformVolumeTiers",
        help_text="Faixas de volume customizadas [{\"max\": 1000, \"rateCents\": 50}, ...]",
    )
    notes = models.TextField(
        null=True, blank=True, help_text="Termos contratuais e observações financeiras."
    )
    status = models.CharField(
        max_length=20,
        choices=OperatorStatus.choices,
        default=OperatorStatus.TRIAL,
        help_text="Status atual da assinatura/contrato na plataforma.",
    )
    createdAt = models.DateTimeField(auto_now_add=True, db_column="createdAt")
    updatedAt = models.DateTimeField(auto_now=True, db_column="updatedAt")

    class Meta:
        db_table = "Operator"
        managed = False
        verbose_name = "Operador Logístico"
        verbose_name_plural = "Operadores Logísticos"

    def __str__(self):
        return self.name

    def calculate_platform_fee(self, completed_deliveries_count: int) -> dict:
        """
        Calcula o custo da plataforma SaaS para o operador no mês,
        aplicando faixas de volume (se houver) ou a taxa por entrega,
        com garantia irrevogável do piso mínimo mensal.
        """
        floor_cents = self.platformMinMonthlyFloorCents if self.platformMinMonthlyFloorCents is not None else 29900
        rate_cents = self.platformCostPerDeliveryCents if self.platformCostPerDeliveryCents is not None else 40
        tiers = self.platformVolumeTiers or []

        calculated_cents = 0
        if tiers and isinstance(tiers, list):
            remaining = completed_deliveries_count
            prev_max = 0
            for tier in tiers:
                tier_max = tier.get("max")
                tier_rate = tier.get("rateCents", rate_cents)
                if tier_max is None:
                    calculated_cents += remaining * tier_rate
                    break
                else:
                    span = tier_max - prev_max
                    qty_in_tier = min(remaining, span)
                    calculated_cents += qty_in_tier * tier_rate
                    remaining -= qty_in_tier
                    prev_max = tier_max
                    if remaining <= 0:
                        break
        else:
            calculated_cents = completed_deliveries_count * rate_cents

        final_fee_cents = max(calculated_cents, floor_cents)
        applied_floor = (final_fee_cents == floor_cents) and (calculated_cents < floor_cents)

        return {
            "deliveries_count": completed_deliveries_count,
            "calculated_cents": calculated_cents,
            "floor_cents": floor_cents,
            "final_fee_cents": final_fee_cents,
            "final_fee_reais": round(final_fee_cents / 100.0, 2),
            "floor_reais": round(floor_cents / 100.0, 2),
            "base_rate_reais": round(rate_cents / 100.0, 2),
            "applied_floor": applied_floor,
        }


class PlatformAdmin(models.Model):
    """
    Administradores globais da Plataforma (Expresso Neves).

    Têm o poder de fazer bypass no RLS do PostgreSQL e gerenciar Operadores,
    auditorias e configurações globais com soberania absoluta sobre todos os tenants.
    """

    id = models.UUIDField(primary_key=True, editable=False)
    supabase_uid = models.UUIDField(
        null=True, blank=True, help_text="Identificador legado Supabase Auth (opcional)."
    )
    name = models.CharField(max_length=255, help_text="Nome completo do administrador.")
    email = models.CharField(
        max_length=255, unique=True, help_text="E-mail de login corporativo."
    )
    passwordHash = models.CharField(
        max_length=255, null=True, blank=True, db_column="passwordHash", help_text="Hash PBKDF2 da senha de acesso."
    )
    createdAt = models.DateTimeField(auto_now_add=True, db_column="createdAt")

    class Meta:
        db_table = "PlatformAdmin"
        managed = False
        verbose_name = "Administrador da Plataforma"
        verbose_name_plural = "Administradores da Plataforma"

    def __str__(self):
        return f"{self.name} ({self.email})"

    def set_password(self, raw_password: str):
        from accounts.security import hash_password
        self.passwordHash = hash_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        from accounts.security import verify_password
        return verify_password(raw_password, self.passwordHash)


class OperatorAuditLog(models.Model):
    """
    Trilha de auditoria (Audit Log) para mudanças críticas nos Operadores.

    Registra quem alterou o quê (como suspensão de contas), garantindo conformidade
    e rastreabilidade das ações executadas pelos PlatformAdmins.
    """

    id = models.UUIDField(primary_key=True, editable=False)
    operator = models.ForeignKey(
        Operator,
        on_delete=models.CASCADE,
        db_column="operator_id",
        help_text="Operador afetado.",
    )
    platformAdmin = models.ForeignKey(
        PlatformAdmin,
        on_delete=models.RESTRICT,
        db_column="platformAdminId",
        help_text="Administrador que executou a ação.",
    )
    action = models.CharField(
        max_length=100, help_text="Tipo da ação (ex: STATUS_CHANGE)."
    )
    previousStatus = models.CharField(
        max_length=20,
        choices=Operator.OperatorStatus.choices,
        null=True,
        db_column="previousStatus",
    )
    newStatus = models.CharField(
        max_length=20,
        choices=Operator.OperatorStatus.choices,
        null=True,
        db_column="newStatus",
    )
    reason = models.TextField(help_text="Justificativa obrigatória para a mudança.")
    createdAt = models.DateTimeField(auto_now_add=True, db_column="createdAt")

    class Meta:
        db_table = "OperatorAuditLog"
        managed = False
        verbose_name = "Log de Auditoria"
        verbose_name_plural = "Logs de Auditoria"


class StaffMember(TimeStampedTenantModel):
    """
    Membros da equipe interna de um Operador Logístico (Tenants).

    Representa os usuários que operam o painel administrativo (despachantes, gerentes,
    atendimento). Cada membro tem um papel (Role) que delimita seus acessos na aplicação.
    """

    class RoleType(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        MANAGER = "MANAGER", "Manager"
        OPERATOR_ROLE = "OPERATOR_ROLE", "Operator"
        VIEWER = "VIEWER", "Viewer"

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    supabase_uid = models.UUIDField(
        null=True, blank=True, help_text="Vínculo legado Supabase Auth (opcional)."
    )
    name = models.CharField(max_length=255, help_text="Nome do funcionário.")
    email = models.CharField(max_length=255, help_text="E-mail de acesso.")
    passwordHash = models.CharField(
        max_length=255, null=True, blank=True, db_column="passwordHash", help_text="Hash PBKDF2 da senha de acesso."
    )
    role = models.CharField(
        max_length=20, choices=RoleType.choices, default=RoleType.OPERATOR_ROLE
    )
    active = models.BooleanField(
        default=True, help_text="Define se o acesso está ativo ou revogado."
    )
    is_platform_admin: bool = False

    class Meta:
        db_table = "StaffMember"
        managed = False
        verbose_name = "Membro da Equipe"
        verbose_name_plural = "Membros da Equipe"

    def __str__(self):
        return f"{self.name} - {self.role}"

    def set_password(self, raw_password: str):
        from accounts.security import hash_password
        self.passwordHash = hash_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        from accounts.security import verify_password
        return verify_password(raw_password, self.passwordHash)


class SecurityDenylist(models.Model):
    """
    Lista de bloqueios de segurança persistida em banco (Source of Truth).

    Usada para revogar e expurgar Device Tokens ou interceptar IPs maliciosos na Fast Lane.
    Sincroniza-se com o Redis (Layer 1 de cache) mas se mantém como base definitiva
    para sobrevivência a reboots.
    """

    id = models.UUIDField(primary_key=True, editable=False)
    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    targetId = models.UUIDField(
        db_column="targetId",
        help_text="ID do artefato bloqueado (ex: ID do Device Token).",
    )
    targetType = models.CharField(
        max_length=50,
        db_column="targetType",
        help_text="Tipo do bloqueio (ex: DEVICE_TOKEN, IP).",
    )
    reason = models.TextField(
        help_text="Motivo do bloqueio (ex: Suspeita de fraude, Token vazado)."
    )
    blockedAt = models.DateTimeField(auto_now_add=True, db_column="blockedAt")
    expiresAt = models.DateTimeField(
        null=True,
        blank=True,
        db_column="expiresAt",
        help_text="Data de expiração do bloqueio, se aplicável.",
    )

    class Meta:
        db_table = "SecurityDenylist"
        managed = False
        verbose_name = "Bloqueio de Segurana"
        verbose_name_plural = "Bloqueios de Segurana"
