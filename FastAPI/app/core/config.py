from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    POSTGRES_URI: str
    POSTGRES_DB: str = "postgres"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()