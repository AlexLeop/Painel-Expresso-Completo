from django.apps import AppConfig


class TodosConfig(AppConfig):
    default_auto_field = "django.db.models.UUIDField"
    name = "todos"
    verbose_name = "Sistema de Gerenciamento de Tarefas"
