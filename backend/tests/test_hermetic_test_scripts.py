"""Regression tests for scripts that pytest discovers by filename."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_pytest_collection_does_not_import_manual_script_gis_shim():
    """Manual diagnostics must not mutate Django modules during collection."""

    assert "scripts.test_apis" not in sys.modules
    assert "tests.fake_gis" not in sys.modules


def import_script(script_name: str):
    script_path = BACKEND_ROOT / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(
        f"hermetic_{script_path.stem}", script_path
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "script_name",
    ["test_payout_endpoints.py", "test_prod_auth.py"],
)
def test_live_script_import_is_inert(script_name, monkeypatch):
    def fail_on_network(*_args, **_kwargs):
        raise AssertionError("network access attempted during module import")

    monkeypatch.setattr("urllib.request.urlopen", fail_on_network)
    monkeypatch.setattr("socket.create_connection", fail_on_network)

    module = import_script(script_name)

    assert module.__test__ is False


@pytest.mark.parametrize(
    "script_name",
    ["test_payout_endpoints.py", "test_prod_auth.py"],
)
def test_live_script_requires_explicit_opt_in(script_name, monkeypatch):
    monkeypatch.delenv("RUN_LIVE_PRODUCTION_TESTS", raising=False)
    module = import_script(script_name)

    with pytest.raises(RuntimeError, match="disabled"):
        module._require_live_configuration()


def test_vps_url_does_not_fall_back_to_application_database(monkeypatch):
    monkeypatch.setenv("RUN_LIVE_VPS_TESTS", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql://application-db/should-not-be-used")
    monkeypatch.delenv("LIVE_VPS_DATABASE_URL", raising=False)

    from tests import test_vps_database_schema

    with pytest.raises(pytest.fail.Exception, match="LIVE_VPS_DATABASE_URL"):
        test_vps_database_schema.get_vps_db_url()


def test_live_scripts_contain_no_embedded_credentials():
    source = "\n".join(
        (BACKEND_ROOT / "scripts" / name).read_text(encoding="utf-8")
        for name in ("test_payout_endpoints.py", "test_prod_auth.py")
    )

    forbidden_fragments = (
        "@expressoneves",
        "@gmail.com",
        "eyJhbGciOi",
        "supabase.co",
        "easypanel.host",
    )
    assert all(fragment not in source for fragment in forbidden_fragments)
