# Novo Frontend

Frontend web administrativo e operacional da plataforma Expresso Neves.

## Escopo

- Painel para perfis administrativos, operadores, financeiro e gestão operacional.
- Build SPA com Vite.
- Bundle do servidor com `esbuild`.

## Scripts

- `npm run dev`: ambiente local.
- `npm run build`: build de produção do frontend e bundle do servidor.
- `npm run start`: sobe o bundle gerado em `dist/server.cjs`.
- `npm run lint`: valida TypeScript com `tsc --noEmit`.

## Pré-requisitos

- Node.js 20+
- Dependências instaladas com `npm install`

## Execução Local

1. Instale dependências com `npm install`
2. Configure variáveis de ambiente necessárias para autenticação e API
3. Execute `npm run dev`

## Qualidade e Produção

- O build de produção deve passar em `npm run build`.
- A validação estática deve passar em `npm run lint`.
- O contrato da API consumida por este frontend está em `../docs/API_CONTRACT.md`.

## Observações

- Este projeto não depende de AI Studio.
- Qualquer credencial sensível deve ficar fora do repositório e ser injetada via ambiente.
