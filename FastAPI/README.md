# SISREC FastAPI


## Setup sem venv (Windows PowerShell)

1. Ir para a pasta do projeto:
	`cd C:\ISEP\Projetos\SISREC\FastAPI`

2. Instalar dependencias no Python atual:
	`py -m pip install -r requirements.txt`

3. Arrancar a API sem ativar venv:
	`py -m uvicorn app.main:app --reload`

4. Arrancar frontend
cd frontend
npm run dev

5. 
`cd C:\ISEP\Projetos\SISREC\FastAPI`
criar .env
POSTGRES_URI=postgresql://postgres:DtujlICQk2Jc@vsgate-s1.dei.isep.ipp.pt:10305/postgres
POSTGRES_DB=postgres

## Recommendation Endpoints

Base URL local: `http://127.0.0.1:8000`

- Personalized: `/recommendations/user/{user_id}?limit=10&meal_period=auto`
- Hybrid Full: `/recommendations/hybrid/full/{user_id}?limit=10&meal_period=auto`
- Global fallback: `/recommendations?limit=10&meal_period=auto`

`meal_period` aceita: `auto`, `lunch`, `dinner`.

## Hybrid Mode Status

Atualmente, apenas o modo híbrido completo está ativo na API e no frontend:

- Ativo: `/recommendations/hybrid/full/{user_id}`
- Removidos: `/recommendations/hybrid/content/{user_id}` e `/recommendations/hybrid/profile/{user_id}`
