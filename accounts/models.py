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
        TRIAL = 'TRIAL', 'Trial'
        ACTIVE = 'ACTIVE', 'Active'
        SUSPENDED = 'SUSPENDED', 'Suspended'
        CANCELED = 'CANCELED', 'Canceled'

    id = models.UUIDField(primary_key=True, editable=False)
    name = models.CharField(max_length=255, help_text="Razão Social ou Nome Fantasia do Operador Logístico.")
    status = models.CharField(
        max_length=20,
        choices=OperatorStatus.choices,
        default=OperatorStatus.TRIAL,
        help_text="Status atual da assinatura/contrato na plataforma."
    )
    createdAt = models.DateTimeField(auto_now_add=True, db_column='createdAt')
    updatedAt = models.DateTimeField(auto_now=True, db_column='updatedAt')

    class Meta:
        db_table = 'Operator'
        managed = False
        verbose_name = "Operador Logístico"
        verbose_name_plural = "Operadores Logísticos"

    def __str__(self):
        return self.name


class PlatformAdmin(models.Model):
    """
    Administradores globais da Plataforma (Expresso Neves).
    
    Têm o poder de fazer bypass no RLS do PostgreSQL e gerenciar Operadores,
    auditorias e configurações globais. O vínculo com a identidade real é feito
    através do `supabase_uid` gerado pelo Supabase Auth.
    """
    id = models.UUIDField(primary_key=True, editable=False)
    supabase_uid = models.UUIDField(unique=True, help_text="Identificador único no Supabase Auth.")
    name = models.CharField(max_length=255, help_text="Nome completo do administrador.")
    email = models.CharField(max_length=255, unique=True, help_text="E-mail de login corporativo.")
    createdAt = models.DateTimeField(auto_now_add=True, db_column='createdAt')

    class Meta:
        db_table = 'PlatformAdmin'
        managed = False
        verbose_name = "Administrador da Plataforma"
        verbose_name_plural = "Administradores da Plataforma"

    def __str__(self):
        return f"{self.name} ({self.email})"


class OperatorAuditLog(models.Model):
    """
    Trilha de auditoria (Audit Log) para mudanças críticas nos Operadores.

    Registra quem alterou o quê (como suspensão de contas), garantindo conformidade
    e rastreabilidade das ações executadas pelos PlatformAdmins.
    """
    id = models.UUIDField(primary_key=True, editable=False)
    operator = models.ForeignKey(Operator, on_delete=models.CASCADE, db_column='operator_id', help_text="Operador afetado.")
    platformAdmin = models.ForeignKey(PlatformAdmin, on_delete=models.RESTRICT, db_column='platformAdminId', help_text="Administrador que executou a ação.")
    action = models.CharField(max_length=100, help_text="Tipo da ação (ex: STATUS_CHANGE).")
    previousStatus = models.CharField(max_length=20, choices=Operator.OperatorStatus.choices, null=True, db_column='previousStatus')
    newStatus = models.CharField(max_length=20, choices=Operator.OperatorStatus.choices, null=True, db_column='newStatus')
    reason = models.TextField(help_text="Justificativa obrigatória para a mudança.")
    createdAt = models.DateTimeField(auto_now_add=True, db_column='createdAt')

    class Meta:
        db_table = 'OperatorAuditLog'
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
        ADMIN = 'ADMIN', 'Admin'
        MANAGER = 'MANAGER', 'Manager'
        OPERATOR_ROLE = 'OPERATOR_ROLE', 'Operator'
        VIEWER = 'VIEWER', 'Viewer'

    operator = models.ForeignKey(Operator, on_delete=models.CASCADE, db_column='operator_id')
    supabase_uid = models.UUIDField(unique=True, help_text="Vínculo com o login seguro no Supabase Auth.")
    name = models.CharField(max_length=255, help_text="Nome do funcionário.")
    email = models.CharField(max_length=255, help_text="E-mail de acesso.")
    role = models.CharField(max_length=20, choices=RoleType.choices, default=RoleType.OPERATOR_ROLE)
    active = models.BooleanField(default=True, help_text="Define se o acesso está ativo ou revogado.")

    class Meta:
        db_table = 'StaffMember'
        managed = False
        verbose_name = "Membro da Equipe"
        verbose_name_plural = "Membros da Equipe"

    def __str__(self):
        return f"{self.name} - {self.role}"


class SecurityDenylist(models.Model):
    """
    Lista de bloqueios de segurança persistida em banco (Source of Truth).

    Usada para revogar e expurgar Device Tokens ou interceptar IPs maliciosos na Fast Lane.
    Sincroniza-se com o Redis (Layer 1 de cache) mas se mantém como base definitiva 
    para sobrevivência a reboots.
    """
    id = models.UUIDField(primary_key=True, editable=False)
    operator = models.ForeignKey(Operator, on_delete=models.CASCADE, db_column='operator_id')
    targetId = models.UUIDField(db_column='targetId', help_text="ID do artefato bloqueado (ex: ID do Device Token).")
    targetType = models.CharField(max_length=50, db_column='targetType', help_text="Tipo do bloqueio (ex: DEVICE_TOKEN, IP).")
    reason = models.TextField(help_text="Motivo do bloqueio (ex: Suspeita de fraude, Token vazado).")
    blockedAt = models.DateTimeField(auto_now_add=True, db_column='blockedAt')
    expiresAt = models.DateTimeField(null=True, blank=True, db_column='expiresAt', help_text="Data de expiração do bloqueio, se aplicável.")

    class Meta:
        db_table = 'SecurityDenylist'
        managed = False
        verbose_name = "Bloqueio de Segurana"
        verbose_name_plural = "Bloqueios de Segurana"
