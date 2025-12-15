# Backend - Supermercado Multiagente (FastAPI)

## Correr
```bash
cd backend
python -m venv .venv
# Windows:
# .venv\Scripts\activate
# Linux/Mac:
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Endpoints
- GET  `/api/map`
- POST `/api/reset?voucher=150&algo=astar`
- POST `/api/step?n=1`

Algoritmos: `bfs`, `dijkstra`, `astar`
