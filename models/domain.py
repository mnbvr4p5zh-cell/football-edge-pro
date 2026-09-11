from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class TeamSnapshot:
    name: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: float
    goals_against: float
    xg_for: Optional[float] = None
    xg_against: Optional[float] = None
    shots: Optional[float] = None
    shots_on_target: Optional[float] = None
    corners: Optional[float] = None
    cards: Optional[float] = None
    clean_sheet_rate: Optional[float] = None
    btts_rate: Optional[float] = None
    over25_rate: Optional[float] = None
    ppg: Optional[float] = None
    goal_difference: Optional[float] = None
    rest_days: Optional[float] = None
    injuries: int = 0
    suspensions: int = 0
    lineup_strength: float = 1.0
    elo: Optional[float] = None
    recent_form: list = field(default_factory=list)

@dataclass
class Match:
    id: str
    kickoff: datetime
    league: str
    home: str
    away: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    home_xg: Optional[float] = None
    away_xg: Optional[float] = None
    status: str = "NS"
    extra: dict = field(default_factory=dict)

@dataclass
class MarketQuote:
    market: str
    selection: str
    odds: float
    bookmaker: str = "Manual"

@dataclass
class Prediction:
    p_home: float
    p_draw: float
    p_away: float
    exp_home_goals: float
    exp_away_goals: float
    p_over15: float
    p_over25: float
    p_over35: float
    p_btts: float
    p_under25: float
    confidence: float
    model_agreement: float = 0.0
    data_quality: float = 0.0
