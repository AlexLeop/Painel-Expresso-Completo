from django.test import TestCase
from django.utils import timezone


class TodoBasicTests(TestCase):
    def test_todo_app_exists(self):
        """Verifica que o app todos está configurado"""
        from django.apps import apps
        app_config = apps.get_app_config("todos")
        self.assertEqual(app_config.name, "todos")
        self.assertEqual(app_config.verbose_name, "Sistema de Gerenciamento de Tarefas")
