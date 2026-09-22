import tempfile
from pathlib import Path
import pytest
from scripts.audit_release_authority import run_audit, audit_document, is_superseded


def test_is_superseded_detection():
    content_with_banner = "# SUPERSEDED — HISTÓRICO — NÃO AUTORIZA GO-LIVE\nConteúdo legado..."
    assert is_superseded(content_with_banner) is True

    content_without_banner = "# Documento Normal\nSistema Apto Para Produção sem banner..."
    assert is_superseded(content_without_banner) is False


def test_audit_detects_unbanned_conflict():
    with tempfile.TemporaryDirectory() as tmpdir:
        docs_dir = Path(tmpdir)
        authority_file = docs_dir / "V2.md"
        authority_file.write_text("# Plano Mestre V2\nÚnica autoridade", encoding="utf-8")

        conflicting_file = docs_dir / "matriz_antiga.md"
        conflicting_file.write_text("# Matriz\nSISTEMA APTO PARA PRODUÇÃO", encoding="utf-8")

        success, reports = run_audit(docs_dir, authority_file)
        assert success is False
        classifications = [r["classification"] for r in reports]
        assert "CONFLICT_UNBANNED" in classifications


def test_audit_passes_with_superseded_banner():
    with tempfile.TemporaryDirectory() as tmpdir:
        docs_dir = Path(tmpdir)
        authority_file = docs_dir / "V2.md"
        authority_file.write_text("# Plano Mestre V2\nÚnica autoridade", encoding="utf-8")

        banned_file = docs_dir / "matriz_antiga.md"
        banned_file.write_text(
            "# SUPERSEDED — HISTÓRICO — NÃO AUTORIZA GO-LIVE\nSISTEMA APTO PARA PRODUÇÃO histórico.",
            encoding="utf-8",
        )

        success, reports = run_audit(docs_dir, authority_file)
        assert success is True
        classifications = [r["classification"] for r in reports if r["path"] == str(banned_file)]
        assert classifications == ["ARCHIVED_OR_HISTORICAL"]


def test_audit_real_repo_docs():
    repo_root = Path(__file__).resolve().parent.parent.parent
    docs_dir = repo_root / "docs"
    authority_file = docs_dir / "PLANO_IMPLEMENTACAO_PRONTIDAO_PRODUCAO_V2.md"

    assert authority_file.exists(), "PLANO_IMPLEMENTACAO_PRONTIDAO_PRODUCAO_V2.md deve existir"

    success, reports = run_audit(docs_dir, authority_file)
    conflicts = [r for r in reports if r.get("classification") in ("CONFLICT_UNBANNED", "MISSING_AUTHORITY")]
    assert success is True, f"Repositório possui conflitos de autoridade: {conflicts}"
