from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    postgres_user: str = "uniassist"
    postgres_password: str = "change-me"
    postgres_db: str = "uniassist"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    redis_host: str = "localhost"
    redis_port: int = 6379

    # Railway/Render/Heroku kabi platformalar bitta tayyor DATABASE_URL/REDIS_URL
    # beradi — bo'lsa shundan foydalaniladi, aks holda yuqoridagi POSTGRES_*/REDIS_*
    # qismlaridan yig'iladi (docker-compose / mahalliy dev uchun).
    database_url_override: str | None = Field(default=None, alias="DATABASE_URL")
    redis_url_override: str | None = Field(default=None, alias="REDIS_URL")

    bot_token: str = ""

    admin_username: str = "admin"
    admin_password: str = "change-me"
    admin_secret_key: str = "change-me-to-a-random-string"
    admin_host: str = "0.0.0.0"
    admin_port: int = 8000

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            url = self.database_url_override
            # Railway/Heroku odatda "postgres://" yoki asyncpg'siz "postgresql://" beradi.
            if url.startswith("postgres://"):
                url = "postgresql+asyncpg://" + url[len("postgres://") :]
            elif url.startswith("postgresql://"):
                url = "postgresql+asyncpg://" + url[len("postgresql://") :]
            return url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return self.redis_url_override or f"redis://{self.redis_host}:{self.redis_port}/0"


settings = Settings()
