#!/usr/bin/env python3
"""
Criação/Atualização do PlatformAdmin (Superadmin Soberano) em PostgreSQL Standalone.
Utiliza autenticação nativa com PBKDF2-SHA256 e banco de dados PostgreSQL PostGIS local.
Não depende de nenhum serviço externo ou Supabase.
"""

import os
import sys
import uuid
from pathlib import Path
from typing import Optional

# Configurar Django environment
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from accounts.models import PlatformAdmin


def create_admin(
    email: str = "master@expressoneves.com",
    raw_password: Optional[str] = None,
    name: str = "Admin Mestre",
):
    actual_password: Optional[str] = raw_password or os.environ.get("MASTER_ADMIN_PASSWORD")
    if not actual_password:
        print("[ERRO] MASTER_ADMIN_PASSWORD não definido no ambiente.")
        sys.exit(1)

    clean_email = email.strip().lower()

    admin, created = PlatformAdmin.objects.get_or_create(
        email=clean_email,
        defaults={
            "id": uuid.uuid4(),
            "name": name,
        },
    )

    admin.name = name
    admin.set_password(actual_password)
    admin.save()

    action_desc = "CRIADO" if created else "ATUALIZADO"
    print(f"[+] PlatformAdmin '{clean_email}' (ID: {admin.id}) {action_desc} com sucesso no PostgreSQL Standalone.")


if __name__ == "__main__":
    create_admin()
