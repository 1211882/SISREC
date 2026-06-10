# SISREC — Sistema de Recomendação Híbrido (FastAPI + React)

Sistema de recomendação de restaurantes (dataset Yelp) com uma Web API em
FastAPI e um frontend em React/Vite.

## Estrutura

- `app/` — Web API (FastAPI + SQLAlchemy + PostgreSQL)
- `frontend/` — SPA React (Vite)
- `data/` — ficheiros do dataset
- `recommendation_experiments.ipynb` — avaliação (RMSE, Precision/Recall/MAP/NDCG)

## Setup do backend (Windows PowerShell)

1. Instalar dependências:
   ```powershell
   py -m pip install -r requirements.txt
   ```

2. Criar o ficheiro `.env` a partir do exemplo e preencher os valores:
   ```powershell
   Copy-Item .env.example .env
   ```
   Campos:
   - `POSTGRES_URI` — string de ligação ao PostgreSQL
   - `POSTGRES_DB` — nome da base de dados
   - `SECRET_KEY` — chave de assinatura JWT (gerar uma aleatória):
     ```powershell
     py -c "import secrets; print(secrets.token_urlsafe(48))"
     ```
   - `CORS_ORIGINS` — origens permitidas (URLs do frontend)

   > O `.env` está em `.gitignore` e **não deve** ser versionado.

3. Arrancar a API:
   ```powershell
   py -m uvicorn app.main:app --reload
   ```
   Docs interativas: `http://127.0.0.1:8000/docs`

## Setup do frontend

```powershell
cd frontend
npm install
npm run dev
```

## Migrações de base de dados (Alembic)

O esquema é gerido com Alembic. Para o **arranque rápido** em dev, a API ainda
cria as tabelas em falta no startup; o caminho canónico é, porém, o Alembic.

```powershell
# Base de dados nova:
py -m alembic upgrade head

# Base de dados que JÁ tem as tabelas (criadas pelo bootstrap):
py -m alembic stamp head

# Criar uma nova migração após alterar os modelos:
py -m alembic revision --autogenerate -m "descreve a alteracao"
```

A migração inicial (`alembic/versions/0001_initial_schema.py`) cria todas as
tabelas a partir dos modelos. O URL da BD vem das settings (`.env`).

## Testes

```powershell
# Backend (funções puras: JWT, scoring, híbrido)
py -m pytest tests/ -q

# Frontend (helpers de api.js e ProtectedRoute)
cd frontend; npm run test
```

## Autenticação e autorização

- `POST /auth/register` e `POST /auth/login` devolvem um **JWT** (`access_token`).
- O frontend guarda o token e envia-o em `Authorization: Bearer <token>`.
- Endpoints sobre dados de um utilizador (perfil, preferências, amigos, reviews
  e recomendações personalizadas) exigem token válido **e** verificam que o
  recurso pertence ao utilizador autenticado (403 caso contrário).
- O registo inclui um **inquérito de cold-start** opcional (categorias, cidade e
  faixa de preço) para construir o perfil inicial.

## Endpoints de recomendação

Base URL local: `http://127.0.0.1:8000`

- Não personalizado (público): `GET /recommendations?limit=10&meal_period=auto`
- Personalizado (CF, autenticado): `GET /recommendations/user/{user_id}`
- Híbrido completo (autenticado): `GET /recommendations/hybrid/full/{user_id}`
- Previsão de rating (autenticado): `GET /recommendations/predict/{user_id}/{business_id}`
- Utilizadores semelhantes (autenticado): `GET /recommendations/similar-users/{user_id}`

`meal_period` aceita: `auto`, `lunch`, `dinner`.

## Solução híbrida

Tipo: **weighted hybrid**. O score final combina:

| Componente            | Peso |
|-----------------------|------|
| Collaborative (CF)    | 0.50 |
| Content-based (CBF)   | 0.20 |
| Perfil (categorias)   | 0.15 |
| Social (amigos)       | 0.15 |

Adicionalmente, as preferências de **cidade** e **faixa de estrelas** são
aplicadas como filtros com fallback (se um filtro esvaziasse a lista, é
ignorado para garantir resultados). A componente social só é usada quando o
utilizador tem `use_friends_boost` ativo e amigos com reviews.
