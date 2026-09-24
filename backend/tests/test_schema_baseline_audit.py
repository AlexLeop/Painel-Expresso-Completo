from pathlib import Path

from scripts.audit_schema_baseline import (
    FINGERPRINTS,
    classify,
    recommend_baseline,
    validate_fingerprint_manifest,
)


def test_fingerprint_manifest_covers_every_canonical_migration_in_order():
    migrations_dir = Path(__file__).resolve().parents[2] / "database" / "migrations"
    validate_fingerprint_manifest(migrations_dir)


def test_every_migration_has_at_least_one_read_only_probe():
    assert FINGERPRINTS
    assert all(item.probes for item in FINGERPRINTS)
    assert all(
        probe.sql.lstrip().upper().startswith("SELECT")
        for item in FINGERPRINTS
        for probe in item.probes
    )


def test_probe_result_classification():
    assert classify([True, True]) == "APPLIED"
    assert classify([False, False]) == "MISSING"
    assert classify([True, False]) == "PARTIAL"


def test_baseline_requires_contiguous_applied_prefix():
    assert recommend_baseline(
        [("001.sql", "APPLIED"), ("002.sql", "APPLIED"), ("003.sql", "MISSING")]
    ) == "002.sql"
    assert recommend_baseline(
        [("001.sql", "APPLIED"), ("002.sql", "PARTIAL"), ("003.sql", "MISSING")]
    ) is None
    assert recommend_baseline(
        [("001.sql", "APPLIED"), ("002.sql", "MISSING"), ("003.sql", "APPLIED")]
    ) is None
