from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "ipl-predict"
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    MONGO_URI: str
    DB_NAME: str

    REDIS_URL: str = "redis://localhost:6379/0"

    GOOGLE_CLIENT_ID: str = "YOUR_GOOGLE_CLIENT_ID_HERE"

    CRICKET_API_BASE: str = "https://api.cricketapi.com/v1"
    CRICKET_API_KEY: str = "YOUR_API_KEY"

    POLL_INTERVAL_SECONDS: int = 5
    SCORING_EXACT: int = 10
    SCORING_NEAR: int = 5
    MAX_PREDICTIONS_PER_USER: int = 24

    class Config:
        env_file = ".env"

settings = Settings()
