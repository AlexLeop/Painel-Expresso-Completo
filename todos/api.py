from ninja import Router
from typing import List
from uuid import UUID
from django.db import transaction
from django.utils import timezone

from .models import Todo, TodoCategory
from .schemas import (
    TodoIn, TodoUpdate, TodoOut,
    TodoCategoryIn, TodoCategoryOut
)
from accounts.auth import require_role

router = Router(tags=["Todos"])


# ── Endpoints de Categorias ────────────────────────────────────────────────────────
@router.post("/categories", response=TodoCategoryOut)
def create_category(request, payload: TodoCategoryIn):
    staff = require_role(["ADMIN", "MANAGER"])(request)
    with transaction.atomic():
        category = TodoCategory.objects.create(
            operator=staff.operator,
            name=payload.name,
            color=payload.color
        )
        return category


@router.get("/categories", response=List[TodoCategoryOut])
def list_categories(request):
    staff = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
    return TodoCategory.objects.filter(operator=staff.operator)


# ── Endpoints de Tarefas Core ──────────────────────────────────────────────────────
@router.post("/", response=TodoOut)
def create_todo(request, payload: TodoIn):
    staff = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE"])(request)
    with transaction.atomic():
        # Criar tarefa
        todo = Todo.objects.create(
            operator=staff.operator,
            title=payload.title,
            description=payload.description,
            category_id=payload.category_id,
            priority=payload.priority,
            due_date=payload.due_date,
            created_by=staff,
            related_store_id=payload.related_store_id,
            related_client_id=payload.related_client_id
        )
        return todo


@router.get("/", response=List[TodoOut])
def list_todos(request):
    staff = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
    return Todo.objects.filter(
        operator=staff.operator
    ).select_related("category").order_by("-due_date", "-createdAt")


@router.put("/{todo_id}", response=TodoOut)
def update_todo(request, todo_id: UUID, payload: TodoUpdate):
    staff = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE"])(request)
    with transaction.atomic():
        todo = Todo.objects.get(id=todo_id, operator=staff.operator)

        # Atualizar campos
        for field, value in payload.dict(exclude_unset=True).items():
            setattr(todo, field, value)

        # Atualizar completedAt se status for COMPLETED
        if payload.status == "COMPLETED":
            todo.completedAt = timezone.now()
        elif payload.status in ["PENDING", "IN_PROGRESS", "ON_HOLD"]:
            todo.completedAt = None

        todo.save()
        return todo


@router.delete("/{todo_id}")
def delete_todo(request, todo_id: UUID):
    staff = require_role(["ADMIN", "MANAGER"])(request)
    with transaction.atomic():
        todo = Todo.objects.get(id=todo_id, operator=staff.operator)
        todo.delete()
        return {"success": True}
