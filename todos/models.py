from django.db import models
from config.core_models import TenantModel, TimeStampedTenantModel
from accounts.models import Operator, StaffMember
from logistics.models import Driver, Client, Store


class TodoCategory(TenantModel):
    """Categoria das tarefas (ex: Despacho, Financeiro, Manutenção)"""

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    name = models.CharField(max_length=255)
    color = models.CharField(max_length=20, default="#3B82F6")  # Hex color

    class Meta:
        db_table = "TodoCategory"
        managed = False
        verbose_name = "Categoria de Tarefa"
        verbose_name_plural = "Categorias de Tarefas"

    def __str__(self):
        return self.name


class Todo(TimeStampedTenantModel):
    """Tarefa principal"""

    class TodoStatus(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        IN_PROGRESS = "IN_PROGRESS", "Em Andamento"
        COMPLETED = "COMPLETED", "Concluída"
        CANCELLED = "CANCELLED", "Cancelada"
        ON_HOLD = "ON_HOLD", "Em Espera"

    class TodoPriority(models.TextChoices):
        LOW = "LOW", "Baixa"
        MEDIUM = "MEDIUM", "Média"
        HIGH = "HIGH", "Alta"
        URGENT = "URGENT", "Urgente"

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(
        TodoCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column="category_id",
    )
    priority = models.CharField(
        max_length=20, choices=TodoPriority.choices, default=TodoPriority.MEDIUM
    )
    status = models.CharField(
        max_length=20, choices=TodoStatus.choices, default=TodoStatus.PENDING
    )
    due_date = models.DateTimeField(null=True, blank=True)
    completedAt = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        StaffMember,
        on_delete=models.RESTRICT,
        db_column="created_by_id",
        related_name="todos_created",
    )
    # Para tarefas associadas a lojas/clientes
    related_store = models.ForeignKey(
        Store,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        db_column="related_store_id",
    )
    related_client = models.ForeignKey(
        Client,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        db_column="related_client_id",
    )

    class Meta:
        db_table = "Todo"
        managed = False
        verbose_name = "Tarefa"
        verbose_name_plural = "Tarefas"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(due_date__isnull=True)
                | models.Q(due_date__gte=models.F("createdAt")),
                name="todo_due_date_after_created",
            )
        ]

    def __str__(self):
        return self.title


class TodoAssignment(TimeStampedTenantModel):
    """Atribuição de tarefa a usuários (staff, motoristas)"""

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    todo = models.ForeignKey(
        Todo, on_delete=models.CASCADE, db_column="todo_id", related_name="assignments"
    )
    assigned_to_staff = models.ForeignKey(
        StaffMember,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        db_column="assigned_to_staff_id",
        related_name="assigned_todo_assignments",
    )
    assigned_to_driver = models.ForeignKey(
        Driver,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        db_column="assigned_to_driver_id",
        related_name="assigned_todo_assignments",
    )
    assigned_by = models.ForeignKey(
        StaffMember,
        on_delete=models.RESTRICT,
        db_column="assigned_by_id",
        related_name="created_todo_assignments",
    )

    class Meta:
        db_table = "TodoAssignment"
        managed = False
        verbose_name = "Atribuição de Tarefa"
        verbose_name_plural = "Atribuições de Tarefas"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(assigned_to_staff__isnull=False)
                    ^ models.Q(assigned_to_driver__isnull=False)
                ),
                name="todo_assignment_single_assignee",
            )
        ]
