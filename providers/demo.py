from datetime import date, datetime, timedelta
from app.providers.base import FootballProvider
from app.models.domain import Match, TeamSnapshot

class DemoProvider(FootballProvider):
    def fixtures(self, day: date) -> list[Match]:
        base = datetime.combine(day, datetime.min.time())
        return [
            Match("demo-1", base + timedelta(hours=20, minutes=15), "Liga Portugal", "Benfica", "Sporting CP"),
            Match("demo-2", base + timedelta(hours=18), "Premier League", "Arsenal", "Liverpool"),
            Match("demo-3", base + timedelta(hours=21), "La Liga", "Real Madrid", "Barcelona"),
            Match("demo-4", base + timedelta(hours=19, minutes=45), "Serie A", "Inter", "Juventus"),
            Match("demo-5", base + timedelta(hours=17, minutes=30), "Bundesliga", "Bayern München", "Borussia Dortmund"),
            Match("demo-6", base + timedelta(hours=20), "Ligue 1", "Paris Saint-Germain", "Marseille"),
        ]

    def team_snapshot(self, team_name: str, before: date | None = None, limit: int = 12) -> TeamSnapshot:
        seed = sum(ord(c) for c in team_name) % 11
        wins=min(limit, 5 + seed % 5); draws=min(3,max(1,limit-wins)//2); losses=max(0,limit-wins-draws)
        gf=1.42 + seed * 0.075; ga=.72 + (10-seed)*.045
        return TeamSnapshot(
            name=team_name, played=limit, wins=wins, draws=draws, losses=losses,
            goals_for=gf, goals_against=ga,
            xg_for=1.38 + seed*.068, xg_against=.76 + (10-seed)*.038,
            shots=10.8 + seed*.72, shots_on_target=3.9 + seed*.34,
            corners=4.2 + seed*.21, cards=1.6 + (seed%5)*.22,
            clean_sheet_rate=min(.68,.24+seed*.035), btts_rate=min(.79,.40+seed*.024),
            over25_rate=min(.84,.44+seed*.028), ppg=(3*wins+draws)/max(1,limit),
            goal_difference=gf-ga, rest_days=5+(seed%4), injuries=seed%3,
            suspensions=1 if seed in (3,8) else 0, lineup_strength=.96+(seed%5)*.015,
            elo=1460+seed*24, recent_form=list("WWDLW" if seed>5 else "WDLWD")
        )
