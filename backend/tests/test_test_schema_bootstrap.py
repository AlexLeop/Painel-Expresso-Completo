"""Regression coverage for the shared unmanaged-model SQLite bootstrap."""

import pytest
from django.db import connection


@pytest.fixture(autouse=True)
def setup_legacy_operator_and_store_schema(db):
    """Simulate an older module-local schema that predates white-label."""

    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS "Operator" (
                id CHAR(32) PRIMARY KEY,
                name VARCHAR(255) NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS "Store" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                name VARCHAR(255) NOT NULL
            )
            """
        )


@pytest.mark.django_db
def test_bootstrap_upgrades_legacy_schema_before_test_body():
    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names(cursor))
        operator_columns = {
            column.name
            for column in connection.introspection.get_table_description(
                cursor, "Operator"
            )
        }
        integration_columns = {
            column.name
            for column in connection.introspection.get_table_description(
                cursor, "StoreIntegration"
            )
        }

    assert "slug" in operator_columns
    assert {
        "operator_branding",
        "integration_connector",
        "StoreIntegration",
        "integration_webhook_log",
    }.issubset(tables)
    assert {
        "connector_id",
        "webhook_secret",
        "config",
        "auto_create_order",
        "last_webhook_at",
        "error_count",
        "error_message",
    }.issubset(integration_columns)
    assert connection.ops.Adapter(None, geography=True) is None
    assert connection.ops.Adapter("POINT(-46 -23)", geography=True) == (
        "POINT(-46 -23)"
    )
