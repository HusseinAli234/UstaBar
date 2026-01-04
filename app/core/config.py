from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, computed_field
from pydantic_core import MultiHostUrl



class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    PROJECT_NAME: str = "UstaBar"
    DATABASE_URL: str
    BOT_TOKEN: str
    BASE_URL: str = "https://ustabar.pp.ua" 
    WEBHOOK_PATH: str = "/webhook/telegram"
    # POSTGRES_SERVER: str = "db"
    # POSTGRES_USER: str = "user"
    # POSTGRES_PASSWORD: str = "password"
    # POSTGRES_DB: str = "subscription_app"
    # POSTGRES_PORT: int = 5432
    # @computed_field
    # @property
    # def DATABASE_URL(self) -> str:
    #     return str(
    #         MultiHostUrl.build(
    #             scheme="postgresql+asyncpg",
    #             username=self.POSTGRES_USER,
    #             password=self.POSTGRES_PASSWORD,
    #             host=self.POSTGRES_SERVER,
    #             port=self.POSTGRES_PORT,
    #             path=self.POSTGRES_DB,
    #         )
    #     )
    SECRET_KEY: str = "super_secret_key_change_me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

settings = Settings()