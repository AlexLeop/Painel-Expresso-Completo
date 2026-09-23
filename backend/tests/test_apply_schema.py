from pathlib import Path

import pytest

from scripts.apply_schema import (
    MigrationError,
    discover_migrations,
    migrations_through,
    validate_history,
)


def write_migration(directory: Path, name: str, sql: bytes = b"SELECT 1;\n") -> Path:
    path = directory / name
    path.write_bytes(sql)
    return path


def test_discover_migrations_is_ordered_and_normalises_line_endings(tmp_path):
    write_migration(tmp_path, "20260102000000_second.sql", b"SELECT 2;\r\n")
    write_migration(tmp_path, "20260101000000_first.sql", b"SELECT 1;\n")

    migrations = discover_migrations(tmp_path)

    assert [migration.name for migration in migrations] == [
        "20260101000000_first.sql",
        "20260102000000_second.sql",
    ]
    assert migrations[1].sql == "SELECT 2;\n"


def test_validate_history_rejects_modified_applied_migration(tmp_path):
    write_migration(tmp_path, "20260101000000_first.sql")
    migration = discover_migrations(tmp_path)[0]

    with pytest.raises(MigrationError, match="Checksum mismatch"):
        validate_history([migration], {migration.name: "0" * 64})


def test_validate_history_rejects_migration_missing_from_release(tmp_path):
    write_migration(tmp_path, "20260101000000_first.sql")
    migrations = discover_migrations(tmp_path)

    with pytest.raises(MigrationError, match="absent from this release"):
        validate_history(migrations, {"20250101000000_removed.sql": "0" * 64})


def test_validate_history_returns_only_pending_in_order(tmp_path):
    write_migration(tmp_path, "20260101000000_first.sql")
    write_migration(tmp_path, "20260102000000_second.sql")
    migrations = discover_migrations(tmp_path)

    pending = validate_history(migrations, {migrations[0].name: migrations[0].checksum})

    assert [migration.name for migration in pending] == [migrations[1].name]


def test_validate_history_rejects_a_gap_in_the_applied_prefix(tmp_path):
    write_migration(tmp_path, "20260101000000_first.sql")
    write_migration(tmp_path, "20260102000000_second.sql")
    migrations = discover_migrations(tmp_path)

    with pytest.raises(MigrationError, match="contiguous ordered prefix"):
        validate_history(
            migrations,
            {migrations[1].name: migrations[1].checksum},
        )


def test_baseline_must_match_an_exact_migration_filename(tmp_path):
    write_migration(tmp_path, "20260101000000_first.sql")
    migrations = discover_migrations(tmp_path)

    with pytest.raises(MigrationError, match="not a migration filename"):
        migrations_through(migrations, "20260101000000")


def test_baseline_records_only_ordered_prefix(tmp_path):
    write_migration(tmp_path, "20260101000000_first.sql")
    write_migration(tmp_path, "20260102000000_second.sql")
    write_migration(tmp_path, "20260103000000_third.sql")
    migrations = discover_migrations(tmp_path)

    baseline = migrations_through(migrations, "20260102000000_second.sql")

    assert [migration.name for migration in baseline] == [
        "20260101000000_first.sql",
        "20260102000000_second.sql",
    ]


@pytest.mark.parametrize(
    "name",
    ["manual.sql", "2026_UPPER.sql", "20260101000000-hyphen.sql"],
)
def test_discovery_rejects_noncanonical_names(tmp_path, name):
    write_migration(tmp_path, name)

    with pytest.raises(MigrationError, match="Invalid migration filename"):
        discover_migrations(tmp_path)
