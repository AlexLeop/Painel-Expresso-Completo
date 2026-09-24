"""Shared pytest support for the backend test suite.

Production schema is owned by the PostgreSQL migrations under ``database/``.
Several older unit-test modules, however, create small ``managed=False`` table
subsets in SQLite.  When a model gains a nullable column (or a new unmanaged
companion table), those local subsets otherwise drift and fail before their
fixtures can create any data.

The PostgreSQL migration is deliberately *not* executed here: it contains
PostgreSQL-only UUID/JSONB, RLS, policy and function syntax.  This compatibility
bootstrap is additive, SQLite-only, and derives no production behaviour.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from django.db.backends.base.base import BaseDatabaseWrapper


def _table_columns(connection: "BaseDatabaseWrapper", table_name: str) -> set[str]:
    """Return the columns currently available on an SQLite test table."""

    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(
            cursor, table_name
        )
    return {column.name for column in description}


def _add_column_if_missing(
    connection: "BaseDatabaseWrapper",
    table_name: str,
    column_name: str,
    definition: str,
) -> None:
    """Apply an additive SQLite column change without masking other DB errors."""

    if column_name in _table_columns(connection, table_name):
        return

    quoted_table = connection.ops.quote_name(table_name)
    quoted_column = connection.ops.quote_name(column_name)
    with connection.cursor() as cursor:
        cursor.execute(
            f"ALTER TABLE {quoted_table} ADD COLUMN {quoted_column} {definition}"
        )


def _sqlite_geometry_adapter(value, **_kwargs):
    """Serialize GIS values for TEXT columns in the SQLite unit-test schema.

    GeoDjango's ``PointField`` delegates the final conversion to
    ``connection.ops.Adapter``.  The plain SQLite backend intentionally has no
    spatial adapter, while these unit tests model geometry columns as TEXT.
    Keeping this shim on the test connection avoids production-code branches
    for a test-only database limitation.
    """

    if value is None:
        return None
    return str(value)


def _install_sqlite_geometry_contract() -> None:
    """Install the GeoDjango operations expected by the SQLite test double.

    Django can recreate or replace a test connection between fixture phases.
    Installing these attributes at the start of every test keeps GIS writes
    deterministic instead of depending on which schema fixture ran first.
    """

    from django.db import connection

    if connection.vendor != "sqlite":
        return

    if not hasattr(connection.ops, "select"):
        connection.ops.select = "%s"
    if not hasattr(connection.ops, "get_geom_placeholder"):
        connection.ops.get_geom_placeholder = (
            lambda _field, _value, _compiler: "%s"
        )
    if not hasattr(connection.ops, "Adapter"):
        connection.ops.Adapter = _sqlite_geometry_adapter


def _ensure_sqlite_managed_false_schema() -> bool:
    """Bring legacy SQLite table subsets up to the shared unmanaged schema.

    Returns ``True`` once the anchor ``Operator`` table exists and compatibility
    has been applied.  Returning ``False`` lets the fixture hook try again after
    the module-local table bootstrap has run.
    """

    from django.db import connection

    if connection.vendor != "sqlite":
        return False

    _install_sqlite_geometry_contract()

    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names(cursor))

    if "Operator" not in tables:
        return False

    # SQLite cannot add a column with a UNIQUE constraint.  Add the nullable
    # column first, then enforce the Django field's uniqueness with an index.
    _add_column_if_missing(connection, "Operator", "slug", "VARCHAR(100) NULL")
    if "ClientPortalUser" in tables:
        _add_column_if_missing(
            connection, "ClientPortalUser", "active", "BOOLEAN NOT NULL DEFAULT 1"
        )
    with connection.cursor() as cursor:
        cursor.execute(
            'CREATE UNIQUE INDEX IF NOT EXISTS "test_operator_slug_unique" '
            'ON "Operator" ("slug") WHERE "slug" IS NOT NULL'
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS operator_branding (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL UNIQUE,
                brand_name VARCHAR(255) NOT NULL,
                logo_url VARCHAR(500),
                favicon_url VARCHAR(500),
                color_primary VARCHAR(7) NOT NULL DEFAULT '#6366f1',
                color_secondary VARCHAR(7) NOT NULL DEFAULT '#4f46e5',
                color_accent VARCHAR(7) NOT NULL DEFAULT '#f59e0b',
                color_background VARCHAR(7) NOT NULL DEFAULT '#ffffff',
                color_surface VARCHAR(7) NOT NULL DEFAULT '#f4f4f5',
                color_text VARCHAR(7) NOT NULL DEFAULT '#18181b',
                dark_color_background VARCHAR(7) NOT NULL DEFAULT '#0a0a0a',
                dark_color_surface VARCHAR(7) NOT NULL DEFAULT '#171717',
                dark_color_text VARCHAR(7) NOT NULL DEFAULT '#fafafa',
                theme_mode VARCHAR(10) NOT NULL DEFAULT 'light',
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS integration_connector (
                id CHAR(32) PRIMARY KEY,
                slug VARCHAR(50) NOT NULL UNIQUE,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                icon_url VARCHAR(500),
                auth_type VARCHAR(30) NOT NULL DEFAULT 'webhook_signature',
                config_schema TEXT NOT NULL DEFAULT '{}',
                webhook_path_template VARCHAR(200) NOT NULL,
                capabilities TEXT NOT NULL DEFAULT '["receive_orders"]',
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                documentation_url VARCHAR(500),
                version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    # StoreIntegration predates the connector registry.  Do not create its
    # domain anchor until a legacy fixture has provided Store; once available,
    # create the complete current shape so CREATE TABLE IF NOT EXISTS cannot
    # leave a partial version behind for a later test module.
    if "Store" not in tables:
        return True

    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS "StoreIntegration" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                store_id CHAR(32) NOT NULL,
                connector_id CHAR(32),
                provider VARCHAR(50),
                "clientId" VARCHAR(255),
                "clientSecret" TEXT,
                "merchantId" VARCHAR(100),
                "authMode" VARCHAR(30) DEFAULT 'WEBHOOK',
                "baseUrl" TEXT,
                "webhookUrl" TEXT,
                "apiKey" TEXT,
                webhook_secret TEXT,
                config TEXT NOT NULL DEFAULT '{}',
                auto_create_order BOOLEAN NOT NULL DEFAULT 1,
                last_webhook_at TIMESTAMP,
                error_count INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                active BOOLEAN NOT NULL DEFAULT 1,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    store_integration_columns = {
        "connector_id": "CHAR(32)",
        "webhook_secret": "TEXT",
        "config": "TEXT NOT NULL DEFAULT '{}'",
        "auto_create_order": "BOOLEAN NOT NULL DEFAULT 1",
        "last_webhook_at": "TIMESTAMP",
        "error_count": "INTEGER NOT NULL DEFAULT 0",
        "error_message": "TEXT",
    }
    for column_name, definition in store_integration_columns.items():
        _add_column_if_missing(
            connection,
            "StoreIntegration",
            column_name,
            definition,
        )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS integration_webhook_log (
                id CHAR(32) PRIMARY KEY,
                integration_id CHAR(32) NOT NULL,
                connector_slug VARCHAR(50) NOT NULL,
                raw_payload_hash VARCHAR(64) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'received',
                order_id CHAR(32),
                error_detail TEXT,
                processing_ms INTEGER,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS test_webhook_log_dedup_unique
            ON integration_webhook_log (integration_id, raw_payload_hash)
            """
        )

    return True


def pytest_runtest_setup(item):
    """Prepare the SQLite GIS contract before any data fixture can execute."""

    _install_sqlite_geometry_contract()


@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef, request):
    """Run compatibility immediately after a legacy table fixture succeeds.

    A normal autouse fixture is not sufficient: fixtures that insert model data
    can run before it.  Wrapping fixture setup lets us upgrade the table as soon
    as the module's schema fixture has created it and before dependent fixtures
    insert rows.
    """

    outcome = yield
    if outcome.excinfo is not None:
        return

    # The pytest-django blocker is still active after early session fixtures,
    # even though ``django_db_setup`` appears in the closure.  Restrict the
    # compatibility pass to the module-local schema bootstrap itself: at this
    # point its ``db`` dependency is active and the tables have just been made.
    if not fixturedef.argname.startswith("setup_"):
        return
    if not set(fixturedef.argnames).intersection({"db", "transactional_db"}):
        return
    if getattr(request.node, "_managed_false_schema_ready", False):
        return

    if _ensure_sqlite_managed_false_schema():
        request.node._managed_false_schema_ready = True
