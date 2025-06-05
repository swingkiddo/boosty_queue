from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DISCORD_TOKEN: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str
    ADMIN_ID: int

    class Config:
        env_file = ".env"

config = Settings()
