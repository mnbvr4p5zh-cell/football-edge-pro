from datetime import date, datetime
import requests, numpy as np
from app.providers.base import FootballProvider
from app.models.domain import Match, TeamSnapshot

class ApiFootballProvider(FootballProvider):
    BASE="https://v3.football.api-sports.io"
    def __init__(self, key:str):
        if not key: raise ValueError("API_FOOTBALL_KEY não configurado")
        self.headers={"x-apisports-key":key}
    def _get(self,path,params=None):
        r=requests.get(self.BASE+path, headers=self.headers, params=params or {}, timeout=25); r.raise_for_status(); return r.json().get("response",[])
    def fixtures(self, day:date)->list[Match]:
        out=[]
        for x in self._get("/fixtures",{"date":day.isoformat()}):
            f=x["fixture"]; t=x["teams"]; l=x["league"]; g=x.get("goals",{})
            out.append(Match(str(f["id"]), datetime.fromisoformat(f["date"]), l["name"], t["home"]["name"], t["away"]["name"], g.get("home"), g.get("away"), status=f["status"]["short"], extra=x))
        return out
    def team_snapshot(self, team_name:str, before:date|None=None, limit:int=12)->TeamSnapshot:
        teams=self._get("/teams",{"search":team_name})
        if not teams: raise ValueError(f"Equipa não encontrada: {team_name}")
        tid=teams[0]["team"]["id"]
        rows=self._get("/fixtures",{"team":tid,"last":limit})
        gf=[];ga=[];results=[]
        for x in rows:
            home=x["teams"]["home"]["id"]==tid; g=x.get("goals",{}); a=g.get("home") if home else g.get("away"); b=g.get("away") if home else g.get("home")
            if a is not None and b is not None: gf.append(a);ga.append(b);results.append((a,b))
        n=max(1,len(results)); mean=lambda a,d:float(np.mean(a)) if a else d
        return TeamSnapshot(team_name,n,sum(a>b for a,b in results),sum(a==b for a,b in results),sum(a<b for a,b in results),mean(gf,1.4),mean(ga,1.1),None,None,12,4.5,5,2,sum(b==0 for a,b in results)/n if results else .3,sum(a>0 and b>0 for a,b in results)/n if results else .5,sum(a+b>2 for a,b in results)/n if results else .5)
