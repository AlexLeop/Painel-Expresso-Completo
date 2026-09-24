"""Apply the canonical PostgreSQL schema migrations exactly once.

The application models are predominantly ``managed = False``.  Django's
migration ledger therefore is not authoritative for the SQL files in
``database/migrations``.  This runner gives those files their own immutable,
checksummed ledger and serialises deploys with a PostgreSQL advisory lock.

Existing installations that pre-date the ledger must explicitly set
``SCHEMA_MIGRATION_BASELINE`` to the last SQL filename already applied.  The
runner deliberately refuses to guess: silently replaying the initial schema or
silently marking an unapplied migration as complete are both unsafe.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import psycopg


RUNNER_VERSION = "1"
LEDGER_TABLE = "schema_migration"
# Stable signed bigint derived from "expresso-neves-schema-migrations".
ADVISORY_LOCK_ID = 3_882_743_934_412_701_109
MIGRATION_NAME_RE = re.compile(r"^(?P<version>\d{8,14})_[a-z0-9][a-z0-9_]*\.sql$")


class MigrationError(RuntimeError):
    """Raised when applying migrations would be unsafe."""


@dataclass(frozen=True)
class Migration:
    name: str
    version: str
    path: Path
    sql: str
    checksum: str


def _normalise_sql(raw: bytes) -> str:
    """Decode SQL deterministically and normalise checkout line endings."""

    return raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def discover_migrations(directory: Path) -> list[Migration]:
    """Return validated migrations in filename order."""

    if not directory.is_dir():
        raise MigrationError(f"Migration directory does not exist: {directory}")

    migrations: list[Migration] = []
    versions: set[str] = set()
    for path in sorted(directory.glob("*.sql"), key=lambda item: item.name):
        match = MIGRATION_NAME_RE.fullmatch(path.name)
        if not match:
            raise MigrationError(
                f"Invalid migration filename {path.name!r}; expected "
                "<8-14 digit version>_<lowercase_name>.sql"
            )
        version = match.group("version")
        if version in versions:
            raise MigrationError(f"Duplicate migration version: {version}")
        versions.add(version)

        sql = _normalise_sql(path.read_bytes())
        if not sql.strip():
            raise MigrationError(f"Migration is empty: {path.name}")
        migrations.append(
            Migration(
                name=path.name,
                version=version,
                path=path,
                sql=sql,
                checksum=hashlib.sha256(sql.encode("utf-8")).hexdigest(),
            )
        )

    if not migrations:
        raise MigrationError(f"No SQL migrations found in: {directory}")
    return migrations


def validate_history(
    migrations: Sequence[Migration], applied: Mapping[str, str]
) -> list[Migration]:
    """Validate immutability and return migrations that still need applying."""

    available = {migration.name: migration for migration in migrations}
    unknown = sorted(set(applied) - set(available))
    if unknown:
        raise MigrationError(
            "Database contains migrations absent from this release: " + ", ".join(unknown)
        )

    for name, checksum in applied.items():
        expected = available[name].checksum
        if checksum != expected:
            raise MigrationError(
                f"Checksum mismatch for applied migration {name}; "
                "applied migrations are immutable"
            )

    expected_prefix = [migration.name for migration in migrations[: len(applied)]]
    if set(applied) != set(expected_prefix):
        raise MigrationError(
            "Migration ledger is not a contiguous ordered prefix; refusing to "
            "apply older migrations after newer ones"
        )

    return [migration for migration in migrations if migration.name not in applied]


def migrations_through(
    migrations: Sequence[Migration], baseline_name: str
) -> list[Migration]:
    """Return the ordered prefix ending at an explicit baseline filename."""

    names = [migration.name for migration in migrations]
    if baseline_name not in names:
        raise MigrationError(
            f"SCHEMA_MIGRATION_BASELINE={baseline_name!r} is not a migration filename"
        )
    return list(migrations[: names.index(baseline_name) + 1])


def resolve_migrations_dir() -> Path:
    configured = os.environ.get("SCHEMA_MIGRATIONS_DIR")
    if configured:
        return Path(configured).expanduser().resolve()

    script_path = Path(__file__).resolve()
    candidates = (
        script_path.parents[2] / "database" / "migrations",  # source checkout
        script_path.parents[1] / "database" / "migrations",  # container image
    )
    return next((path for path in candidates if path.is_dir()), candidates[0])


def _ensure_ledger(connection: psycopg.Connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS public.{LEDGER_TABLE} (
                name TEXT PRIMARY KEY,
                checksum CHAR(64) NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                execution_ms INTEGER NOT NULL,
                runner_version TEXT NOT NULL,
                baselined BOOLEAN NOT NULL DEFAULT FALSE
            )
            """
        )
    connection.commit()


def _load_history(connection: psycopg.Connection) -> dict[str, str]:
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT name, checksum FROM public.{LEDGER_TABLE} ORDER BY name")
        return {name: checksum.strip() for name, checksum in cursor.fetchall()}


def _has_existing_business_schema(connection: psycopg.Connection) -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass(%s) IS NOT NULL", ('public."Operator"',))
        row = cursor.fetchone()
    return bool(row and row[0])


def _record_baseline(
    connection: psycopg.Connection, migrations: Sequence[Migration]
) -> None:
    with connection.cursor() as cursor:
        for migration in migrations:
            cursor.execute(
                f"""
                INSERT INTO public.{LEDGER_TABLE}
                    (name, checksum, execution_ms, runner_version, baselined)
                VALUES (%s, %s, 0, %s, TRUE)
                ON CONFLICT (name) DO NOTHING
                """,
                (migration.name, migration.checksum, RUNNER_VERSION),
            )
    connection.commit()


def _apply_one(connection: psycopg.Connection, migration: Migration) -> None:
    started = time.monotonic()
    try:
        with connection.cursor() as cursor:
            # prepare=False is required for SQL migration files containing
            # multiple statements.
            cursor.execute(migration.sql, prepare=False)
            execution_ms = max(0, round((time.monotonic() - started) * 1000))
            cursor.execute(
                f"""
                INSERT INTO public.{LEDGER_TABLE}
                    (name, checksum, execution_ms, runner_version, baselined)
                VALUES (%s, %s, %s, %s, FALSE)
                """,
                (
                    migration.name,
                    migration.checksum,
                    execution_ms,
                    RUNNER_VERSION,
                ),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def apply_schema(database_url: str, migrations_dir: Path, baseline_name: str | None) -> int:
    migrations = discover_migrations(migrations_dir)
    applied_count = 0

    with psycopg.connect(database_url, application_name="schema-migration-runner") as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_lock(%s)", (ADVISORY_LOCK_ID,))
            connection.commit()

            _ensure_ledger(connection)
            history = _load_history(connection)
            existing_schema = _has_existing_business_schema(connection)

            if not history and existing_schema:
                if not baseline_name:
                    raise MigrationError(
                        "Existing business schema has no migration ledger. Run "
                        "python scripts/audit_schema_baseline.py first and only set "
                        "SCHEMA_MIGRATION_BASELINE to its verified contiguous "
                        "recommendation. The runner will not guess."
                    )
                baseline = migrations_through(migrations, baseline_name)
                _record_baseline(connection, baseline)
                print(f"Baselined {len(baseline)} existing migration(s) through {baseline_name}.")
                history = _load_history(connection)
            elif not history and baseline_name:
                raise MigrationError(
                    "SCHEMA_MIGRATION_BASELINE was supplied for an empty database; "
                    "remove it so the complete schema is created"
                )

            pending = validate_history(migrations, history)
            for migration in pending:
                print(f"Applying {migration.name} ...", flush=True)
                _apply_one(connection, migration)
                applied_count += 1
                print(f"Applied {migration.name}.", flush=True)

            if not pending:
                print("Schema is up to date.")
        finally:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_advisory_unlock(%s)", (ADVISORY_LOCK_ID,))
                connection.commit()
            except Exception:
                connection.rollback()

    return applied_count


def main() -> int:
    database_url = os.environ.get("DIRECT_URL") or os.environ.get("DATABASE_URL")
    if not database_url:
        print("DIRECT_URL or DATABASE_URL must be configured.", file=sys.stderr)
        return 2

    try:
        count = apply_schema(
            database_url=database_url,
            migrations_dir=resolve_migrations_dir(),
            baseline_name=os.environ.get("SCHEMA_MIGRATION_BASELINE") or None,
        )
    except (MigrationError, OSError, psycopg.Error) as exc:
        print(f"Schema migration failed: {exc}", file=sys.stderr)
        return 1

    print(f"Schema migration complete ({count} applied).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
