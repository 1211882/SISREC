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
