import math
from dataclasses import dataclass
import numpy as np
from scipy.stats import poisson
from app.models.domain import TeamSnapshot, Prediction

@dataclass
class ModelComponent:
    name: str
    home_goals: float
    away_goals: float
    weight: float


def _safe(v, fallback):
    return fallback if v is None else float(v)


def _attack(t: TeamSnapshot) -> float:
    xg = _safe(t.xg_for, t.goals_for)
    shots_factor = 1.0 + ((_safe(t.shots_on_target, 4.5) - 4.5) * 0.018)
    return max(.25, (0.64*xg + 0.36*t.goals_for) * shots_factor)


def _defence(t: TeamSnapshot) -> float:
    xga = _safe(t.xg_against, t.goals_against)
    return max(.25, 0.64*xga + 0.36*t.goals_against)


def _ppg(t: TeamSnapshot) -> float:
    if t.ppg is not None:
        return t.ppg
    return (3*t.wins + t.draws) / max(1, t.played)


def _elo_proxy(t: TeamSnapshot) -> float:
    if t.elo is not None:
        return t.elo
    gd = (t.goals_for - t.goals_against)
    return 1450 + 120*(_ppg(t)-1.35) + 70*gd


def _context_factor(t: TeamSnapshot) -> float:
    availability = max(.82, 1.0 - 0.028*t.injuries - 0.035*t.suspensions)
    lineup = min(1.08, max(.86, t.lineup_strength or 1.0))
    rest = 1.0
    if t.rest_days is not None:
        if t.rest_days < 4: rest = .965
        elif t.rest_days >= 7: rest = 1.018
    return availability * lineup * rest


def _components(home: TeamSnapshot, away: TeamSnapshot, home_advantage: float):
    base_h = math.sqrt(_attack(home) * _defence(away)) * home_advantage
    base_a = math.sqrt(_attack(away) * _defence(home)) / math.sqrt(home_advantage)

    ppg_delta = _ppg(home) - _ppg(away)
    form_h = base_h * math.exp(0.075*ppg_delta)
    form_a = base_a * math.exp(-0.075*ppg_delta)

    elo_delta = _elo_proxy(home) - _elo_proxy(away)
    elo_h = base_h * math.exp(elo_delta/2200)
    elo_a = base_a * math.exp(-elo_delta/2200)

    ctx_h = base_h * _context_factor(home) / max(.86, math.sqrt(_context_factor(away)))
    ctx_a = base_a * _context_factor(away) / max(.86, math.sqrt(_context_factor(home)))

    return [
        ModelComponent("xG-Poisson", base_h, base_a, .46),
        ModelComponent("Forma ponderada", form_h, form_a, .22),
        ModelComponent("Elo/força", elo_h, elo_a, .20),
        ModelComponent("Contexto/plantel", ctx_h, ctx_a, .12),
    ]


def dixon_coles_matrix(lh: float, la: float, max_goals: int=8, rho: float=-0.08):
    matrix=np.zeros((max_goals+1,max_goals+1), dtype=float)
    for i in range(max_goals+1):
        for j in range(max_goals+1):
            p=poisson.pmf(i,lh)*poisson.pmf(j,la)
            if i==0 and j==0: p *= max(.01, 1 - lh*la*rho)
            elif i==0 and j==1: p *= max(.01, 1 + lh*rho)
            elif i==1 and j==0: p *= max(.01, 1 + la*rho)
            elif i==1 and j==1: p *= max(.01, 1 - rho)
            matrix[i,j]=p
    total=matrix.sum()
    return matrix/total if total else matrix


def _probs(matrix):
    p_home=float(np.tril(matrix,-1).sum())
    p_draw=float(np.trace(matrix))
    p_away=float(np.triu(matrix,1).sum())
    p_over15=float(sum(matrix[i,j] for i in range(matrix.shape[0]) for j in range(matrix.shape[1]) if i+j>=2))
    p_over25=float(sum(matrix[i,j] for i in range(matrix.shape[0]) for j in range(matrix.shape[1]) if i+j>=3))
    p_over35=float(sum(matrix[i,j] for i in range(matrix.shape[0]) for j in range(matrix.shape[1]) if i+j>=4))
    p_btts=float(matrix[1:,1:].sum())
    return p_home,p_draw,p_away,p_over15,p_over25,p_over35,p_btts


def predict(home: TeamSnapshot, away: TeamSnapshot, home_advantage: float=1.10, max_goals:int=8) -> Prediction:
    comps=_components(home,away,home_advantage)
    lh=sum(c.home_goals*c.weight for c in comps)/sum(c.weight for c in comps)
    la=sum(c.away_goals*c.weight for c in comps)/sum(c.weight for c in comps)
    lh=max(.15,min(4.2,lh)); la=max(.15,min(4.2,la))
    matrix=dixon_coles_matrix(lh,la,max_goals)
    ph,pd,pa,p15,p25,p35,pb=_probs(matrix)

    component_home=[]
    for c in comps:
        m=dixon_coles_matrix(c.home_goals,c.away_goals,max_goals)
        component_home.append(_probs(m)[0])
    disagreement=min(.35,float(np.std(component_home)))
    agreement=max(0.0,1-disagreement/.18)
    completeness=sum(v is not None for v in [home.xg_for,home.xg_against,away.xg_for,away.xg_against,home.shots_on_target,away.shots_on_target]) / 6
    sample=min(1.0,(home.played+away.played)/24)
    quality=.52*completeness+.48*sample
    confidence=max(.35,min(.93,.55*agreement+.45*quality))
    return Prediction(ph,pd,pa,lh,la,p15,p25,p35,pb,1-p25,confidence,agreement,quality)


def score_matrix(pred: Prediction, max_goals:int=6):
    matrix=dixon_coles_matrix(pred.exp_home_goals,pred.exp_away_goals,max_goals)
    rows=[]
    for h in range(max_goals+1):
        for a in range(max_goals+1): rows.append((h,a,float(matrix[h,a])))
    return sorted(rows,key=lambda x:x[2],reverse=True)


def model_components(home: TeamSnapshot, away: TeamSnapshot, home_advantage: float=1.10):
    return [c.__dict__ for c in _components(home, away, home_advantage)]
