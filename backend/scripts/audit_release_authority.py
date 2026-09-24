#!/usr/bin/env python3
"""
Auditor Fail-Closed da Autoridade Documental Ativa (DOC-001 / G0).
Garante que apenas o plano consolidado do sistema sem mobile seja a autoridade normativa ativa,
bloqueando qualquer declaração ativa de aptidão para produção não comprovada.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


FORBIDDEN_ACTIVE_CLAIMS = [
    re.compile(r"SISTEMA\s+APTO\s+PARA\s+PRODU[CÇ][AÃ]O", re.IGNORECASE),
    re.compile(r"AP[OÓ]S\s+GO-LIVE\s+CONTROLADO", re.IGNORECASE),
]

SUPERSEDED_MARKERS = [
    "SUPERSEDED",
    "HISTÓRICO",
    "HISTORICO",
    "NÃO AUTORIZA GO-LIVE",
    "NAO AUTORIZA GO-LIVE",
    "G0–G10 PENDENTES",
    "G0-G10 PENDENTES",
]


def compute_file_hash(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def is_superseded(content: str) -> bool:
    header = content[:1500].upper()
    return any(marker.upper() in header for marker in SUPERSEDED_MARKERS)


def audit_document(filepath: Path, authority_path: Path) -> Tuple[str, Optional[str]]:
    """
    Classifica o documento como:
    - 'AUTHORITY': O documento oficial ativo
    - 'ARCHIVED_OR_HISTORICAL': Documento histórico com banner obrigatório
    - 'CONVENTIONAL_DOC': Documentação técnica ou spec válida
    - 'CONFLICT_UNBANNED': Erro: declaração de aptidão ou plano concorrente sem banner
    """
    if filepath.resolve() == authority_path.resolve():
        return "AUTHORITY", None

    # Se estiver em docs/archive/, deve conter marcador de histórico
    in_archive = "archive" in filepath.parts
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        return "READ_ERROR", f"Não foi possível ler o arquivo: {e}"

    has_superseded_banner = is_superseded(content)

    # Verificar declarações de aptidão proibidas
    for pattern in FORBIDDEN_ACTIVE_CLAIMS:
        if pattern.search(content):
            if not has_superseded_banner:
                return "CONFLICT_UNBANNED", f"Contém declaração de aptidão ativa sem banner SUPERSEDED ({pattern.pattern})"

    if in_archive and not has_superseded_banner:
        return "CONFLICT_UNBANNED", "Arquivo arquivado sem marcador explícito de histórico/superseded"

    if has_superseded_banner:
        return "ARCHIVED_OR_HISTORICAL", None

    return "CONVENTIONAL_DOC", None


def run_audit(docs_dir: Path, authority_file: Path) -> Tuple[bool, List[Dict[str, str]]]:
    reports = []
    has_conflict = False

    if not authority_file.exists():
        reports.append({
            "path": str(authority_file),
            "classification": "MISSING_AUTHORITY",
            "reason": "Arquivo de autoridade documental não foi encontrado",
        })
        return False, reports

    # Registrar a autoridade com seu SHA256
    authority_sha = compute_file_hash(authority_file)
    reports.append({
        "path": str(authority_file),
        "classification": "ACTIVE_AUTHORITY",
        "sha256": authority_sha,
        "reason": "Autoridade normativa mestre confirmada",
    })

    for root, _, files in os.walk(docs_dir):
        for file in files:
            if file.endswith(".md"):
                p = Path(root) / file
                if p.resolve() == authority_file.resolve():
                    continue

                classification, reason = audit_document(p, authority_file)
                entry = {
                    "path": str(p),
                    "classification": classification,
                }
                if reason:
                    entry["reason"] = reason

                if classification in ("CONFLICT_UNBANNED", "READ_ERROR"):
                    has_conflict = True

                reports.append(entry)

    return not has_conflict, reports


def main():
    parser = argparse.ArgumentParser(description="Auditor de autoridade de release DOC-001")
    parser.add_argument("--docs", default="docs", help="Diretório de documentação")
    parser.add_argument(
        "--authority",
        default="docs/PLANO_IMPLEMENTACAO_CORRECOES_SISTEMA_SEM_MOBILE.md",
        help="Caminho do plano mestre vigente (única autoridade)",
    )
    parser.add_argument("--report", default=None, help="Caminho do relatório JSON de saída")
    parser.add_argument("--check", action="store_true", help="Falha com código 1 caso haja conflitos")

    args = parser.parse_args()

    docs_path = Path(args.docs)
    auth_path = Path(args.authority)

    success, reports = run_audit(docs_path, auth_path)

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(reports, f, indent=2, ensure_ascii=False)
        print(f"[AUDIT] Relatório gravado em {report_path}")

    # Log resumo
    conflicts = [r for r in reports if r.get("classification") in ("CONFLICT_UNBANNED", "MISSING_AUTHORITY")]
    if conflicts:
        print(f"[AUDIT] ERRO: {len(conflicts)} conflito(s) de autoridade documental detectado(s):")
        for c in conflicts:
            print(f"  - {c['path']}: {c.get('reason')}")
        if args.check:
            sys.exit(1)
    else:
        print(f"[AUDIT] SUCESSO: Autoridade única verificada ({auth_path}). Zero conflitos.")
        if args.check:
            sys.exit(0)


if __name__ == "__main__":
    main()
