from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_easypanel_backend_uses_single_root_dockerfile():
    dockerfile = REPO_ROOT / "Dockerfile"

    assert dockerfile.is_file(), "O EasyPanel exige Dockerfile na raiz do repositório"
    assert not (REPO_ROOT / "backend" / "Dockerfile").exists(), (
        "Não mantenha uma segunda definição do backend sujeita a drift"
    )

    content = dockerfile.read_text(encoding="utf-8")
    assert "COPY backend/requirements.txt" in content
    assert "COPY backend/ /app/" in content
    assert "COPY database/migrations/ /app/database/migrations/" in content


@pytest.mark.parametrize("compose_name", ["docker-compose.yml", "docker-compose.local.yml"])
def test_compose_uses_easypanel_compatible_backend_dockerfile(compose_name):
    content = (REPO_ROOT / compose_name).read_text(encoding="utf-8")

    assert "dockerfile: backend/Dockerfile" not in content
    assert content.count("dockerfile: Dockerfile") == 4


def test_frontend_dockerfile_uses_repository_root_context():
    content = (REPO_ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")

    assert "COPY frontend/package*.json ./" in content
    assert "COPY frontend/ ./" in content


def test_docker_context_excludes_local_secrets_and_build_caches():
    content = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()

    assert ".env" in content
    assert "**/.venv" in content
    assert "**/node_modules" in content
    assert "mobile" in content
