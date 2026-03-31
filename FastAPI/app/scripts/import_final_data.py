import json
from pathlib import Path

from sqlalchemy import delete

from app.database.session import SessionLocal
from app.models.auth_user_dataset_link import AuthUserDatasetLink
from app.models.business import Business
from app.models.user import User
from app.models.review import Review

BUSINESS_FILE = Path("data/business_final.json")
USER_FILE = Path("data/user_final.json")
REVIEW_FILE = Path("data/review_final.json")

BATCH_SIZE = 1000


def read_json_lines(file_path: Path):
    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def chunks(records, size: int):
    batch = []
    for record in records:
        batch.append(record)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def normalize_record(record: dict, model):
    allowed_keys = model.__table__.columns.keys()
    return {key: value for key, value in record.items() if key in allowed_keys}


def import_file(session, file_path: Path, model, label: str, clear_table: bool = False):
    if not file_path.exists():
        raise FileNotFoundError(f"Ficheiro não encontrado: {file_path}")

    if clear_table:
        session.execute(delete(model))
        session.commit()

    total = 0
    for batch in chunks(read_json_lines(file_path), BATCH_SIZE):
        objects = [model(**normalize_record(record, model)) for record in batch]
        session.add_all(objects)
        session.commit()
        total += len(batch)

    print(f"{label} importados: {total}")


def run_import(clear_tables: bool = False):
    session = SessionLocal()
    try:
        if clear_tables:
            # Limpa na ordem inversa das FKs.
            session.execute(delete(Review))
            session.execute(delete(AuthUserDatasetLink))
            session.execute(delete(User))
            session.execute(delete(Business))
            session.commit()

        print("A importar businesses...")
        import_file(session, BUSINESS_FILE, Business, "Businesses")

        print("A importar users...")
        import_file(session, USER_FILE, User, "Users")

        print("A importar reviews...")
        import_file(session, REVIEW_FILE, Review, "Reviews")

        print("Importação concluída com sucesso.")
    finally:
        session.close()


if __name__ == "__main__":
    # Como o processo pode ter corrido parcialmente antes, limpamos e reimportamos tudo.
    run_import(clear_tables=True)
