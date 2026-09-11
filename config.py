from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    data_provider: str = os.getenv("DATA_PROVIDER", "sportmonks")
    sportmonks_api_token: str = os.getenv("SPORTMONKS_API_TOKEN", "")
    api_football_key: str = os.getenv("API_FOOTBALL_KEY", "")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///data/football_analytics.db")
    default_bankroll: float = float(os.getenv("DEFAULT_BANKROLL", "1000"))

settings = Settings()
