import subprocess

import pytest

from scripts.deploy_release import deployment_commands, run


def test_release_commands_have_a_fixed_fail_fast_order():
    commands = deployment_commands("python-test")

    assert commands == (
        ("python-test", "scripts/apply_schema.py"),
        (
            "python-test",
            "manage.py",
            "migrate",
            "--settings=config.settings_migrate",
            "--noinput",
        ),
        (
            "python-test",
            "manage.py",
            "warmup_denylist",
            "--settings=config.settings_migrate",
        ),
        (
            "python-test",
            "manage.py",
            "collectstatic",
            "--settings=config.settings_migrate",
            "--noinput",
        ),
    )


def test_schema_failure_emits_audit_then_stops(monkeypatch):
    attempted: list[tuple[str, ...]] = []

    def fake_run(command, **kwargs):
        attempted.append(tuple(command))
        if command[1] == "scripts/apply_schema.py":
            raise subprocess.CalledProcessError(9, command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(subprocess.CalledProcessError):
        run(
            (
                ("python-test", "scripts/apply_schema.py"),
                ("python-test", "second.py"),
            )
        )

    assert attempted == [
        ("python-test", "scripts/apply_schema.py"),
        ("python-test", "scripts/audit_schema_baseline.py", "--summary"),
    ]


def test_non_schema_failure_stops_without_baseline_audit(monkeypatch):
    attempted: list[tuple[str, ...]] = []

    def fake_run(command, **kwargs):
        attempted.append(tuple(command))
        raise subprocess.CalledProcessError(9, command)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(subprocess.CalledProcessError):
        run((("python-test", "manage.py", "migrate"),))

    assert attempted == [("python-test", "manage.py", "migrate")]
