def implied_probability(odds: float) -> float:
    return 1/odds if odds and odds>0 else 0

def remove_margin(odds: list[float]) -> list[float]:
    raw=[implied_probability(x) for x in odds]
    s=sum(raw) or 1
    return [x/s for x in raw]

def expected_value(prob: float, odds: float) -> float:
    return prob*odds-1

def kelly_fraction(prob: float, odds: float, fraction: float=.25, cap: float=.05) -> float:
    if odds<=1: return 0
    b=odds-1; q=1-prob; full=(b*prob-q)/b
    return min(cap,max(0,full)*fraction)

def label_ev(ev:float)->str:
    if ev>=.12:return "Value forte"
    if ev>=.06:return "Value moderado"
    if ev>=.02:return "Value ligeiro"
    if ev>=0:return "Marginal"
    return "Sem value"

def clv(opening_odds: float|None, closing_odds: float|None)->float|None:
    if not opening_odds or not closing_odds: return None
    return opening_odds/closing_odds-1
