"""Explicitly opted-in checks against an external VPS database."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.vps_db

LIVE_OPT_IN_ENV = "RUN_LIVE_VPS_TESTS"
LIVE_DATABASE_URL_ENV = "LIVE_VPS_DATABASE_URL"


def get_vps_db_url() -> str:
    """Return an explicitly supplied external URL or skip before any connection."""
    if os.environ.get(LIVE_OPT_IN_ENV) != "1":
        pytest.skip(
            f"Live VPS tests are disabled; set {LIVE_OPT_IN_ENV}=1 to opt in."
        )

    db_url = os.environ.get(LIVE_DATABASE_URL_ENV)
    if not db_url:
        pytest.fail(
            f"{LIVE_DATABASE_URL_ENV} is required when {LIVE_OPT_IN_ENV}=1.",
            pytrace=False,
        )
    return db_url


def connect_to_vps(db_url: str):
    """Import the live-only driver lazily and create the requested connection."""
    import psycopg

    return psycopg.connect(db_url, connect_timeout=10)


def test_vps_postgres_connection_and_postgis():
    with connect_to_vps(get_vps_db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version_row = cur.fetchone()
            assert version_row is not None, "Failed to fetch PostgreSQL version"
            assert "PostgreSQL" in version_row[0]

            cur.execute("SELECT PostGIS_Version();")
            postgis_row = cur.fetchone()
            assert postgis_row is not None, "Failed to fetch PostGIS version"
            assert str(postgis_row[0]).startswith("3.")


def test_vps_required_tables_exist():
    expected_tables = {
        "Operator",
        "PlatformAdmin",
        "StaffMember",
        "Store",
        "Driver",
        "Order",
        "Wallet",
        "WalletTransaction",
        "OperatorInternalWallet",
        "WithdrawalRequest",
        "PayoutPolicyConfig",
        "ServiceZone",
    }

    with connect_to_vps(get_vps_db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )
            tables = {row[0] for row in cur.fetchall()}

    missing_tables = expected_tables - tables
    assert not missing_tables, f"Missing VPS tables: {sorted(missing_tables)}"


def test_vps_auth_password_hash_columns():
    with connect_to_vps(get_vps_db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND column_name = 'passwordHash'
                """
            )
            tables_with_password_hash = {row[0] for row in cur.fetchall()}

    assert {
        "PlatformAdmin",
        "StaffMember",
        "ClientPortalUser",
        "Driver",
    }.issubset(tables_with_password_hash)
