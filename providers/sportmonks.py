from datetime import date, datetime
import requests
from app.providers.base import FootballProvider
from app.models.domain import Match, TeamSnapshot

class SportmonksProvider(FootballProvider):
    BASE = "https://api.sportmonks.com/v3/football"
    def __init__(self, token: str):
        if not token:
            raise ValueError("SPORTMONKS_API_TOKEN não configurado")
        self.token = token

    def _get(self, path: str, params: dict | None = None):
        params = dict(params or {})
        params["api_token"] = self.token
        r = requests.get(self.BASE + path, params=params, timeout=25)
        r.raise_for_status()
        return r.json().get("data", [])

    def fixtures(self, day: date) -> list[Match]:
        ds = day.isoformat()
        rows = self._get(f"/fixtures/date/{ds}", {"include":"participants;league"})
        out=[]
        for x in rows:
            parts=x.get("participants", [])
            home=next((p for p in parts if p.get("meta",{}).get("location")=="home"), {})
            away=next((p for p in parts if p.get("meta",{}).get("location")=="away"), {})
            league=(x.get("league") or {}).get("name", "")
            dt=datetime.fromisoformat(x["starting_at"].replace("Z", "+00:00")) if "T" in x.get("starting_at","") else datetime.fromisoformat(x["starting_at"])
            out.append(Match(str(x["id"]), dt, league, home.get("name","Casa"), away.get("name","Fora"), status=str(x.get("state_id","")), extra=x))
        return out

    def team_snapshot(self, team_name: str, before: date | None = None, limit: int = 12) -> TeamSnapshot:
        # Pesquisa do clube + últimos jogos. Alguns planos/ligas podem exigir permissões específicas.
        teams=self._get("/teams/search/"+requests.utils.quote(team_name))
        if not teams: raise ValueError(f"Equipa não encontrada: {team_name}")
        team_id=teams[0]["id"]
        fixtures=self._get(f"/fixtures/between/{(before or date.today()).replace(day=1).isoformat()}/{(before or date.today()).isoformat()}/{team_id}", {"include":"participants;scores;statistics;xGFixture"})
        finished=fixtures[-limit:]
        gf=[]; ga=[]; xgf=[]; xga=[]; shots=[]; sot=[]; corners=[]; cards=[]; results=[]
        for f in finished:
            parts=f.get("participants",[])
            loc=next((p.get("meta",{}).get("location") for p in parts if p.get("id")==team_id), None)
            opp="away" if loc=="home" else "home"
            # Robust fallback: score extraction differs by include/plan; xG/statistics are optional.
            vals={}
            for s in f.get("scores",[]):
                desc=s.get("description")
                participant=s.get("participant")
                if desc in ("CURRENT","2ND_HALF","FULLTIME") and participant in ("home","away"):
                    vals[participant]=s.get("score",{}).get("goals")
            if loc in vals and opp in vals:
                gf.append(vals[loc]); ga.append(vals[opp]); results.append((vals[loc], vals[opp]))
            for row in f.get("xgfixture",[]) or []:
                v=(row.get("data") or {}).get("value")
                if row.get("location")==loc and v is not None: xgf.append(float(v))
                if row.get("location")==opp and v is not None: xga.append(float(v))
        import numpy as np
        n=max(1,len(gf))
        wins=sum(a>b for a,b in results); draws=sum(a==b for a,b in results); losses=sum(a<b for a,b in results)
        mean=lambda a, d: float(np.mean(a)) if a else d
        return TeamSnapshot(team_name, n, wins, draws, losses, mean(gf,1.4), mean(ga,1.1), mean(xgf,mean(gf,1.4)), mean(xga,mean(ga,1.1)), 12.0,4.5,5.0,2.0, sum(b==0 for a,b in results)/n if results else .3, sum(a>0 and b>0 for a,b in results)/n if results else .5, sum(a+b>2 for a,b in results)/n if results else .5)
