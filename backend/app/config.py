from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    API_ID: int
    API_HASH: str
    ADMIN_USERNAME: str = "@bestiemondia426"
    BOT_NAME: str = "Aviator predict Vector"
    DEFAULT_LANG: str = "fr"
    PREDICTION_INTERVAL: int = 300  # seconds for signals
    COLLECTION_INTERVAL: int = 300  # seconds for scraping/observations
    COLLECTION_RETRIES: int = 3
    REQUEST_BACKOFF_BASE: float = 1.0  # seconds base for exponential backoff
    PROXY_URL: str = ""  # optional proxy (http://user:pass@host:port)
    WEBHOOK_BASE_URL: str = ""  # e.g. https://your-service.onrender.com
    SCRAPE_FAILURE_THRESHOLD: int = 3
    BLACKLIST_DURATION: int = 3600  # seconds to blacklist a failing site
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/app.db"
    SECRET_KEY: str = ""

    # Supprime la classe Config qui charge le .env
    # class Config:
    #     env_file = "../.env"

settings = Settings()
