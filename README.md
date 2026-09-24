# Painel Expresso Neves

Sistema web multi-tenant para operação logística, gestão de lojas e motoboys, corridas, financeiro, white-label e integrações.

## Estrutura canônica

- `backend/`: Django/Ninja, Celery e Fast Lane em `backend/fast_lane/`.
- `frontend/`: painel React/Vite.
- `database/migrations/`: autoridade única das migrations SQL de negócio.
- `docs/`: documentação vigente e índice documental.
- `docker-compose.yml`: topologia canônica de produção.
- `docker-compose.local.yml`: topologia local.
- `mobile/`: legado preservado, fora do escopo do sistema atual e aguardando reimplementação.

## Documentação

Consulte [docs/README.md](docs/README.md). O único plano com autoridade de release é `docs/PLANO_IMPLEMENTACAO_CORRECOES_SISTEMA_SEM_MOBILE.md`.

## Validação local

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q

cd ..\frontend
npx tsc --noEmit
npm run build
npm audit --omit=dev
```

Para validar as definições de containers sem usar credenciais reais:

```powershell
docker compose --env-file .env.example -f docker-compose.yml config -q
docker compose --env-file .env.example -f docker-compose.local.yml config -q
```

Não execute produção com os valores ilustrativos de `.env.example`.

## Migrations em deploy

O deploy executa primeiro o runner SQL canônico e depois as migrations de estado do Django:

```bash
python scripts/apply_schema.py
python manage.py migrate --settings=config.settings_migrate --noinput
python manage.py collectstatic --noinput
```

Um banco existente sem `schema_migration` nunca deve receber baseline por tentativa. Execute a auditoria somente leitura:

```bash
python scripts/audit_schema_baseline.py
```

Configure `SCHEMA_MIGRATION_BASELINE` somente quando o relatório retornar `safe_to_configure_baseline: true`, usando exatamente o arquivo indicado em `recommended_baseline`. Remova essa variável depois que o runner criar e preencher o ledger.
