"""
SCRIPT DESATIVADO / QUARENTENADO (IR-003 / CONCERNS.md)

AVISO CRÍTICO DE SEGURANÇA:
Este script anteriormente iterava por todos os usuários do Supabase Auth e promovia
cada usuário a 'PlatformAdmin' indiscriminadamente, criando uma vulnerabilidade de
escalada de privilégio global.

A promoção de administradores na plataforma Expresso Neves é estritamente unitária,
exige autorização prévia por allowlist em ambiente seguro e geração de evento imutável
em OperatorAuditLog.

NÃO EXECUTAR EM PRODUÇÃO.
"""

import sys

def main():
    print("[BLOQUEADO] sync_all_users.py está desativado permanentemente por violação do princípio de menor privilégio (IR-003).")
    sys.exit(1)

if __name__ == "__main__":
    main()
