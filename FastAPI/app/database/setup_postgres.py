from app.database.session import engine
from app.database.base import Base

from app.models.business import Business
from app.models.auth_user import AuthUser
from app.models.auth_user_dataset_link import AuthUserDatasetLink
from app.models.auth_user_preference import AuthUserPreference
from app.models.user import User
from app.models.review import Review

print("setup_postgres arrancou")
def run_setup():
    try:
        print("A criar tabelas...")
        Base.metadata.create_all(bind=engine)
        print("✔ Tables created!")
    except Exception as e:
        print("❌ Error:", e)


if __name__ == "__main__":
    run_setup()