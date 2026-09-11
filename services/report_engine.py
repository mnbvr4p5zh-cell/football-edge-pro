def build_report(home, away, p, markets, components):
    favorite = home.name if p.p_home > p.p_away else away.name
    fav_prob = max(p.p_home,p.p_away)
    tempo = "aberto" if p.p_over25 >= .58 else "controlado" if p.p_over25 < .46 else "equilibrado"
    both = "há boa probabilidade de ambas marcarem" if p.p_btts >= .57 else "o modelo não vê BTTS como cenário dominante"
    best = next((m for m in sorted(markets,key=lambda x:x.get('ev') if x.get('ev') is not None else -9,reverse=True) if m.get('ev') is not None and m['ev']>0),None)
    value = f"O melhor desvio face ao mercado está em {best['market']}, com EV estimado de {best['ev']*100:.1f}%." if best else "Com as odds fornecidas, não existe value positivo claro segundo o modelo."
    context=[]
    if home.injuries or home.suspensions: context.append(f"{home.name} tem {home.injuries} lesões e {home.suspensions} suspensões contabilizadas")
    if away.injuries or away.suspensions: context.append(f"{away.name} tem {away.injuries} lesões e {away.suspensions} suspensões contabilizadas")
    context_text=(". ".join(context)+". ") if context else ""
    return (
        f"O ensemble coloca {favorite} como lado mais provável ({fav_prob*100:.1f}%), com expectativa de golos de "
        f"{p.exp_home_goals:.2f}-{p.exp_away_goals:.2f}. O perfil do jogo é {tempo}; {both}. "
        f"{context_text}{value} A confiança do modelo é {p.confidence*100:.0f}/100 e depende da qualidade dos dados disponíveis."
    )
