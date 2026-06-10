from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api.routes import auth
from app.api.routes import businesses
from app.api.routes import recommendations
from app.api.routes import reviews
from app.api.routes import users
from app.core.config import settings
from app.database.base import Base
from app.database.session import engine


def _ensure_schema() -> None:
    """Create tables and apply the lightweight column patch on startup.

    NOTE: this is a minimal bootstrap suited to the academic scope. A
    production system should manage schema changes with a migration tool
    (e.g. Alembic) instead of create_all + ad-hoc ALTER.
    """
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    if not inspector.has_table("auth_user_preferences"):
        return

    columns = {column["name"] for column in inspector.get_columns("auth_user_preferences")}
    if "preferred_price_range" in columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE auth_user_preferences "
                "ADD COLUMN IF NOT EXISTS preferred_price_range INTEGER"
            )
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_schema()
    yield


app = FastAPI(title="SISREC API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "SISREC API online"}


app.include_router(reviews.router)
app.include_router(users.router)
app.include_router(businesses.router)
app.include_router(recommendations.router)
app.include_router(auth.router)
