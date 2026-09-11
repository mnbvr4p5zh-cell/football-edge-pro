from abc import ABC, abstractmethod
from datetime import date
from app.models.domain import Match, TeamSnapshot

class FootballProvider(ABC):
    @abstractmethod
    def fixtures(self, day: date) -> list[Match]: ...

    @abstractmethod
    def team_snapshot(self, team_name: str, before: date | None = None, limit: int = 12) -> TeamSnapshot: ...
