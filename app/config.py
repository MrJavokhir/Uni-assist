from pydantic import Field, field_validator
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
    webapp_url: str = "https://example.com/webapp/"

    admin_username: str = "admin"
    admin_password: str = "change-me"
    admin_secret_key: str = "change-me-to-a-random-string"
    admin_host: str = "0.0.0.0"
    admin_port: int = 8000
    # Adminka sessiyasi shuncha daqiqa harakatsizlikdan keyin tugaydi.
    # Sozlama qilib qo'yildi, chunki "qancha bo'lsin" degan savolga javob
    # loyihaga qarab o'zgaradi — kod tegmasdan .env dan boshqariladi.
    admin_session_timeout_minutes: int = 20

    # ---- "Mentordan so'rash" ----
    # Mentorlar forum-guruhi (Topics yoqilgan). Bot u yerda admin va
    # "Mavzularni boshqarish" huquqiga ega bo'lishi shart. Bo'sh bo'lsa
    # funksiya o'chiq: ilovada savol berish tugmasi chiqmaydi.
    mentor_group_id: int | None = None
    # Mentor bo'lish murojaatlari keladigan username (@ siz ham bo'ladi).
    admin_telegram_username: str = ""
    # Javobsiz savollar va shikoyatlar haqida ogohlantirish oladigan admin.
    admin_telegram_id: int | None = None
    # Savol berish mumkin bo'lgan davlatlar (ISO kodlar): "DE,HU,KR,PL".
    active_countries: str = ""
    question_monthly_limit: int = 3
    followup_limit: int = 3
    # Mentor javobida ruxsat etilgan havolalar. "." bilan boshlangani butun
    # domen zonasini bildiradi (".de" — har qanday nemis sayti).
    allowed_link_domains: str = ""

    @field_validator("mentor_group_id", "admin_telegram_id", mode="before")
    @classmethod
    def _empty_id_is_none(cls, value: object) -> object:
        # .env da "MENTOR_GROUP_ID=" kabi bo'sh qoldirilsa ham ishga tushsin.
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def active_country_codes(self) -> list[str]:
        codes = [c.strip().upper() for c in self.active_countries.split(",")]
        return list(dict.fromkeys(c for c in codes if len(c) == 2))

    @property
    def allowed_link_domain_list(self) -> list[str]:
        items = [d.strip().lower() for d in self.allowed_link_domains.split(",")]
        return [d for d in items if d]

    @property
    def admin_contact_username(self) -> str:
        return self.admin_telegram_username.strip().lstrip("@")

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
