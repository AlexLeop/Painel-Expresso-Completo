import importlib

import pytest
from django.db import migrations


@pytest.mark.parametrize(
    "module_name",
    [
        "accounts.migrations.0004_operatorbranding_state",
        "integration.migrations.0002_connector_webhooklog_state",
    ],
)
def test_sql_owned_models_use_state_only_django_migrations(module_name):
    migration_module = importlib.import_module(module_name)
    operations = migration_module.Migration.operations

    assert len(operations) == 1
    assert isinstance(operations[0], migrations.SeparateDatabaseAndState)
    assert operations[0].database_operations == []
    assert operations[0].state_operations

    for operation in operations[0].state_operations:
        assert isinstance(operation, migrations.CreateModel)
        assert operation.options["managed"] is False
