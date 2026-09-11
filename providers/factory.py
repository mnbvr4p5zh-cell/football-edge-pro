from app.config import settings
from app.providers.demo import DemoProvider
from app.providers.sportmonks import SportmonksProvider
from app.providers.api_football import ApiFootballProvider

def get_provider():
    try:
        if settings.data_provider == "sportmonks" and settings.sportmonks_api_token:
            return SportmonksProvider(settings.sportmonks_api_token)
        if settings.data_provider == "api_football" and settings.api_football_key:
            return ApiFootballProvider(settings.api_football_key)
    except Exception:
        pass
    return DemoProvider()
