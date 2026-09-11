from datetime import date, datetime, timedelta
from dataclasses import asdict
from pathlib import Path
from typing import Optional
import math, random

from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, EmailStr

from app.providers.factory import get_provider
from app.services.model_engine import predict, score_matrix, model_components
from app.services.value_engine import implied_probability, expected_value, kelly_fraction, label_ev, remove_margin
from app.services.report_engine import build_report
from app.db import SessionLocal, User, hash_password, verify_password, make_token, parse_token, save_analysis, history

ROOT = Path(__file__).parent
app = FastAPI(title="Football Edge Pro", version="3.0.0")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

class AnalyzeRequest(BaseModel):
    home: str
    away: str
    kickoff_date: Optional[date] = None
    form_games: int = Field(default=12, ge=5, le=30)
    home_advantage: float = Field(default=1.10, ge=.8, le=1.4)
    bankroll: float = Field(default=1000, ge=0)
    home_injuries: int = Field(default=0, ge=0, le=20)
    away_injuries: int = Field(default=0, ge=0, le=20)
    home_suspensions: int = Field(default=0, ge=0, le=10)
    away_suspensions: int = Field(default=0, ge=0, le=10)
    home_rest_days: Optional[float] = Field(default=None, ge=0, le=30)
    away_rest_days: Optional[float] = Field(default=None, ge=0, le=30)
    home_lineup_strength: float = Field(default=1.0, ge=.8, le=1.15)
    away_lineup_strength: float = Field(default=1.0, ge=.8, le=1.15)
    odds_home: Optional[float] = Field(default=None, gt=1)
    odds_draw: Optional[float] = Field(default=None, gt=1)
    odds_away: Optional[float] = Field(default=None, gt=1)
    odds_over15: Optional[float] = Field(default=None, gt=1)
    odds_over25: Optional[float] = Field(default=None, gt=1)
    odds_under25: Optional[float] = Field(default=None, gt=1)
    odds_over35: Optional[float] = Field(default=None, gt=1)
    odds_btts: Optional[float] = Field(default=None, gt=1)

class AuthRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)

def current_user_id(authorization: str|None):
    if not authorization or not authorization.lower().startswith("bearer "): return None
    return parse_token(authorization.split(" ",1)[1])

@app.get("/")
def home(): return FileResponse(ROOT / "static" / "index.html")

@app.get("/api/health")
def health():
    provider=get_provider()
    return {"ok":True,"provider":provider.__class__.__name__,"version":"3.0.0","time":datetime.utcnow().isoformat()+"Z"}

@app.get("/api/fixtures")
def fixtures(day: date = Query(default_factory=date.today)):
    try: rows=get_provider().fixtures(day)
    except Exception as e: raise HTTPException(status_code=502,detail=f"Erro ao obter jogos: {e}")
    return [{"id":m.id,"kickoff":m.kickoff.isoformat(),"league":m.league,"home":m.home,"away":m.away,"status":m.status,"home_score":m.home_score,"away_score":m.away_score} for m in rows]

def market_row(name, probability, odds, bankroll):
    fair=1/probability if probability>0 else None
    if not odds:
        return {"market":name,"probability":probability,"fair_odds":fair,"market_odds":None,"implied":None,"edge":None,"ev":None,"kelly":0,"stake":0,"label":"Sem odd"}
    implied=implied_probability(odds); ev=expected_value(probability,odds); kelly=kelly_fraction(probability,odds,.25,.05)
    return {"market":name,"probability":probability,"fair_odds":fair,"market_odds":odds,"implied":implied,"edge":probability-implied,"ev":ev,"kelly":kelly,"stake":bankroll*kelly,"label":label_ev(ev)}

def apply_context(s, injuries, suspensions, rest, lineup):
    s.injuries=max(s.injuries,injuries); s.suspensions=max(s.suspensions,suspensions)
    if rest is not None:s.rest_days=rest
    s.lineup_strength=lineup
    return s

@app.post("/api/analyze")
def analyze(req:AnalyzeRequest, authorization: str|None=Header(default=None)):
    provider=get_provider()
    try:
        h=provider.team_snapshot(req.home,req.kickoff_date,req.form_games)
        a=provider.team_snapshot(req.away,req.kickoff_date,req.form_games)
        h=apply_context(h,req.home_injuries,req.home_suspensions,req.home_rest_days,req.home_lineup_strength)
        a=apply_context(a,req.away_injuries,req.away_suspensions,req.away_rest_days,req.away_lineup_strength)
        p=predict(h,a,req.home_advantage)
    except Exception as e: raise HTTPException(status_code=502,detail=f"Erro na análise: {e}")
    markets=[
        market_row("Casa",p.p_home,req.odds_home,req.bankroll), market_row("Empate",p.p_draw,req.odds_draw,req.bankroll), market_row("Fora",p.p_away,req.odds_away,req.bankroll),
        market_row("Over 1.5",p.p_over15,req.odds_over15,req.bankroll), market_row("Over 2.5",p.p_over25,req.odds_over25,req.bankroll), market_row("Under 2.5",p.p_under25,req.odds_under25,req.bankroll),
        market_row("Over 3.5",p.p_over35,req.odds_over35,req.bankroll), market_row("Ambas marcam",p.p_btts,req.odds_btts,req.bankroll),
        market_row("1X",p.p_home+p.p_draw,None,req.bankroll), market_row("X2",p.p_away+p.p_draw,None,req.bankroll)
    ]
    components=model_components(h,a,req.home_advantage)
    ranked=sorted(markets,key=lambda x:x["ev"] if x["ev"] is not None else -99,reverse=True)
    fair_margin=None
    if req.odds_home and req.odds_draw and req.odds_away:
        fair_margin=remove_margin([req.odds_home,req.odds_draw,req.odds_away])
    result={
        "home":asdict(h),"away":asdict(a),"prediction":asdict(p),
        "scorelines":[{"home":x,"away":y,"probability":z} for x,y,z in score_matrix(p,6)[:10]],
        "markets":markets,"best_value":ranked[0] if ranked and ranked[0]["ev"] is not None else None,
        "components":components,"market_fair_probabilities":fair_margin,
        "report":build_report(h,a,p,markets,components),
        "model":{"name":"Edge Ensemble v3 · xG + Dixon-Coles + Elo + Contexto","form_games":req.form_games,"home_advantage":req.home_advantage,"notes":"Estimativas probabilísticas; não são garantias nem eliminam risco."}
    }
    try: save_analysis(h.name,a.name,result,current_user_id(authorization))
    except Exception: pass
    return result

@app.get("/api/value-finder")
def value_finder(day: date = Query(default_factory=date.today), bankroll: float=1000):
    provider=get_provider(); out=[]
    for m in provider.fixtures(day)[:12]:
        try:
            h=provider.team_snapshot(m.home,day,12); a=provider.team_snapshot(m.away,day,12); p=predict(h,a)
            # In demo mode these are deterministic simulated market prices, clearly labelled.
            seed=sum(ord(c) for c in (m.home+m.away+day.isoformat())); rnd=random.Random(seed)
            probs=[p.p_home,p.p_draw,p.p_away]
            odds=[]
            for pr in probs:
                market_pr=max(.05,pr*(1+rnd.uniform(-.12,.12))); odds.append(max(1.15,1/(market_pr*1.055)))
            markets=[market_row("Casa",p.p_home,odds[0],bankroll),market_row("Empate",p.p_draw,odds[1],bankroll),market_row("Fora",p.p_away,odds[2],bankroll)]
            best=max(markets,key=lambda x:x["ev"])
            out.append({"fixture":m.id,"kickoff":m.kickoff.isoformat(),"league":m.league,"home":m.home,"away":m.away,"best":best,"confidence":p.confidence,"odds_source":"Simulada em modo demo"})
        except Exception: continue
    return sorted(out,key=lambda x:x["best"]["ev"],reverse=True)

@app.get("/api/backtest/demo")
def backtest_demo(samples:int=Query(250,ge=50,le=2000)):
    rnd=random.Random(42); bets=0; profit=0.0; staked=0.0; brier=[]; clv_vals=[]
    for _ in range(samples):
        p=min(.82,max(.18,rnd.betavariate(3,3))); outcome=1 if rnd.random()<p else 0
        market_p=min(.9,max(.1,p+rnd.gauss(0,.055))); opening=1/(market_p*1.035); closing=1/(min(.92,max(.08,p+rnd.gauss(0,.028)))*1.025)
        ev=p*opening-1; brier.append((p-outcome)**2)
        if ev>.035:
            stake=1.0; bets+=1; staked+=stake; profit += (opening-1)*stake if outcome else -stake; clv_vals.append(opening/closing-1)
    return {"mode":"demo","samples":samples,"bets":bets,"roi":profit/staked if staked else 0,"yield":profit/staked if staked else 0,"profit_units":profit,"brier":sum(brier)/len(brier),"avg_clv":sum(clv_vals)/len(clv_vals) if clv_vals else 0,"hit_rate":None,"note":"Backtest sintético para validar a interface. Para resultados reais, liga histórico de odds/resultados à base de dados."}

@app.get("/api/history")
def get_history(authorization:str|None=Header(default=None)):
    return history(current_user_id(authorization),30)

@app.post("/api/auth/register")
def register(req:AuthRequest):
    with SessionLocal() as db:
        if db.query(User).filter(User.email==req.email.lower()).first(): raise HTTPException(409,"Email já registado")
        u=User(email=req.email.lower(),password_hash=hash_password(req.password)); db.add(u); db.commit(); db.refresh(u)
        return {"token":make_token(u.id),"email":u.email}

@app.post("/api/auth/login")
def login(req:AuthRequest):
    with SessionLocal() as db:
        u=db.query(User).filter(User.email==req.email.lower()).first()
        if not u or not verify_password(req.password,u.password_hash): raise HTTPException(401,"Credenciais inválidas")
        return {"token":make_token(u.id),"email":u.email}
