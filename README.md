# Football Edge Pro v3 — Website

Terminal web de análise avançada de futebol com FastAPI e frontend responsivo.

## Funcionalidades
- Jogos por data via provider configurável
- Sportmonks / API-Football / modo demo
- Ensemble: xG-Poisson + Dixon-Coles + forma + força/Elo + contexto
- Ajustes por lesões, suspensões, descanso e força do provável XI
- 1X2, Over 1.5 / 2.5 / 3.5, Under 2.5, BTTS e placares exatos
- Odds justas, margem, edge, EV e Kelly 1/4 com limite de 5% da banca
- AI Match Report em português (explicação determinística do modelo)
- Value Finder
- Backtesting demo com ROI, Brier Score e CLV
- Histórico persistente de análises
- Registo/login por JWT e passwords com PBKDF2
- SQLite local; preparado para PostgreSQL via `DATABASE_URL`
- Dockerfile + render.yaml para deploy

## Arrancar localmente
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn server:app --host 0.0.0.0 --port 8000
```
Abre `http://127.0.0.1:8000`.

## Dados reais
Sportmonks:
```env
DATA_PROVIDER=sportmonks
SPORTMONKS_API_TOKEN=A_TUA_CHAVE
```
API-Football:
```env
DATA_PROVIDER=api_football
API_FOOTBALL_KEY=A_TUA_CHAVE
```
A disponibilidade de xG, lineups, injuries, odds e estatísticas varia por competição e plano. Sem chave, o site usa `demo`.

## Deploy no Render
O projeto já contém `render.yaml`. Configura `DATA_PROVIDER` e a chave da API. Para persistência séria em produção, liga um PostgreSQL e define `DATABASE_URL`; define também `JWT_SECRET`.

## Nota sobre o scanner de Value
No modo demo, o scanner cria preços de mercado simulados e identifica-os como tal. Não uses esses preços para decisões reais. Quando ligares um provider de odds, substitui essa camada pelas odds reais.

## Testes executados nesta build
- `/api/health`: OK
- `/api/fixtures`: OK
- `/api/analyze`: OK
- `/api/value-finder`: OK
- `/api/backtest/demo`: OK
- registo/login JWT: OK
- histórico por utilizador: OK
- sintaxe JavaScript: OK
- compilação Python: OK
