import os
from pathlib import Path
import subprocess
import sys

from scripts.audit_schema_baseline import (
    FINGERPRINTS,
    classify,
    recommend_baseline,
    validate_fingerprint_manifest,
)


def test_fingerprint_manifest_covers_every_canonical_migration_in_order():
    migrations_dir = Path(__file__).resolve().parents[2] / "database" / "migrations"
    validate_fingerprint_manifest(migrations_dir)


def test_auditor_can_be_executed_directly_without_package_import_failure():
    backend_dir = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment.pop("DIRECT_URL", None)
    environment.pop("DATABASE_URL", None)

    result = subprocess.run(
        [sys.executable, "scripts/audit_schema_baseline.py"],
        cwd=backend_dir,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "DIRECT_URL or DATABASE_URL must be configured." in result.stderr
    assert "ModuleNotFoundError" not in result.stderr


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
