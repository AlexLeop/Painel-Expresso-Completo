from ninja import ModelSchema, Schema
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from .models import Todo, TodoCategory


class TodoCategoryIn(Schema):
    name: str
    color: str = "#3B82F6"


class TodoCategoryOut(ModelSchema):
    class Meta:
        model = TodoCategory
        fields = ["id", "name", "color"]


class TodoIn(Schema):
    title: str
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    priority: Optional[str] = "MEDIUM"
    due_date: Optional[datetime] = None
    related_store_id: Optional[UUID] = None
    related_client_id: Optional[UUID] = None


class TodoUpdate(Schema):
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None


class TodoOut(ModelSchema):
    category: Optional[TodoCategoryOut] = None

    class Meta:
        model = Todo
        fields = "__all__"
