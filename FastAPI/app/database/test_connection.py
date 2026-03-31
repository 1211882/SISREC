from sqlalchemy import text
from app.database.session import engine


def test_connection():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("Ligação com sucesso!")
            print("Resultado:", result.scalar())
    except Exception as e:
        print("Erro na ligação:", e)


if __name__ == "__main__":
    test_connection()