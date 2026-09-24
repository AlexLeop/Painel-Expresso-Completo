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
