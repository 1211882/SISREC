# SISREC FastAPI

## Requisitos
- Python 3.11+ (recomendado 3.11 ou 3.12)
- PostgreSQL acessivel com a string de ligacao no ficheiro `.env`

## Setup do backend (Windows PowerShell)
1. Ir para a pasta do projeto:
	`cd C:\ISEP\Projetos\SISREC\FastAPI`

2. Criar uma venv local (na tua maquina):
	`py -3.12 -m venv .venv`

3. Ativar a venv:
	`.\.venv\Scripts\Activate.ps1`

4. Instalar dependencias:
	`pip install -r requirements.txt`

5. Arrancar a API:
	`uvicorn app.main:app --reload`

## Setup sem venv (Windows PowerShell)
Se preferires nao usar ambiente virtual, podes correr diretamente com o Python instalado no sistema:

1. Ir para a pasta do projeto:
	`cd C:\ISEP\Projetos\SISREC\FastAPI`

2. Instalar dependencias no Python atual:
	`py -m pip install -r requirements.txt`

3. Arrancar a API sem ativar venv:
	`py -m uvicorn app.main:app --reload`

Nota: isto funciona, mas pode misturar dependencias entre projetos no teu Python global.

## Erros comuns de venv
- Erro ao usar `.venv` de outro colega:
  Cada venv e especifica da maquina e do Python instalado. Recria sempre a venv localmente.

- `cannot be loaded because running scripts is disabled`:
  Corre no PowerShell atual:
  `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

- `ModuleNotFoundError: fastapi` (ou outro pacote):
  A venv foi criada mas faltam dependencias. Volta a correr:
  `pip install -r requirements.txt`
