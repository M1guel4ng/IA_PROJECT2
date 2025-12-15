# IA_PROJECT2
🛒 Supermercado Multiagente

Simulador multi-agente donde un comprador usa un vale (voucher) para seleccionar productos, recorrer el supermercado con pathfinding y pagar en caja con ayuda de un cajero.
El frontend muestra la simulación en un Canvas (mapa, rutas, carrito, caja y logs).

✨ Qué hace el proyecto

Carga un mapa de supermercado desde JSON (/data/*.json).

Inicia una simulación con:

BuyerAgent (comprador): elige productos dentro del vale, recorre estantes, junta ítems, va a caja y sale.

CashierAgent (cajero): escanea productos, calcula subtotal, canjea vale y devuelve cambio si corresponde.

Ejecuta la simulación por pasos (step) o “en vivo” desde el frontend.

Registra eventos en una bitácora JSONL (data/bitacora.jsonl).

🧱 Tecnologías
Backend

Lenguaje: Python

Framework: FastAPI

Servidor ASGI: Uvicorn

Dependencias: fastapi, uvicorn[standard], pydantic

Frontend

Lenguajes: HTML + CSS + JavaScript

Render: Canvas 2D (sin frameworks)

📁 Estructura del proyecto
supermercado_multiagente/
├─ backend/
│  ├─ app/
│  │  ├─ main.py            # API FastAPI
│  │  ├─ models.py          # Dataclasses del dominio/estado
│  │  ├─ data_loader.py     # Carga de mapas JSON
│  │  ├─ pathfinding.py     # BFS / Dijkstra / A*
│  │  ├─ bitacora.py        # Log JSONL de eventos
│  │  ├─ strips.py          # Base STRIPS (extensible)
│  │  ├─ agents/
│  │  │  ├─ buyer.py        # Agente comprador
│  │  │  ├─ cashier.py      # Agente cajero
│  │  │  └─ base.py         # Protocolo de agente
│  │  └─ sim/
│  │     ├─ world.py        # Orquestador de simulación
│  │     └─ rules.py        # Helpers/reglas
│  └─ requirements.txt
├─ frontend/
│  ├─ index.html / app.js / styles.css
│  ├─ branch.html / branch.js
└─ data/
   ├─ supermarket_cbba_*.json   # Sucursales/mapas
   └─ bitacora.jsonl

🧠 Modelo y clases principales (Backend)
models.py (modelo de dominio)

Pos: coordenada (x, y) + distancia Manhattan.

Rect: rectángulo (para estantes) + iteración de celdas.

Grid: tamaño, celdas transitables, bloquear/desbloquear.

Shelf: estante con Rect y sección.

Register: caja con cashier_spot y queue_spot.

Section: categoría (ej. “Lácteos”).

Product: sku, nombre, precio, sección, estante, punto de pick.

MapData: empaqueta todo el mapa.

BuyerState: estado del comprador (posición, vale, carrito, ruta, metas, pagado, métricas).

CashierState: estado del cajero (caja activa, escaneos, subtotal, canje, cambio).

WorldState: estado global (mapa + buyer + cashier + mensajes + step).

data_loader.py

load_map(): lee el JSON del supermercado y construye:

Grid con borde bloqueado,

estantes como obstáculos,

cajas y puntos de pick transitables.

pathfinding.py

Algoritmos soportados:

BFS

Dijkstra

A*

Función central: find_path(algo, grid, start, goal)

agents/buyer.py — BuyerAgent

Responsabilidades:

Selecciona productos con estrategia greedy por precio (max cantidad sin exceder vale).

Ordena metas con nearest neighbor (picks cercanos).

Se mueve con el algoritmo elegido (BFS/Dijkstra/A*).

Reglas clave:

Si el vale llega a 0 o ya no alcanza para nada pendiente ⇒ va directo a caja.

En cola de caja ⇒ espera hasta que el cajero marque paid=True.

Después del pago ⇒ va a la salida.

Eventos que registra:

pick (producto recogido)

agents/cashier.py — CashierAgent

Responsabilidades:

Detecta si el comprador está en la cola (queue_spot) de alguna caja.

Escanea 1 producto por tick.

Al terminar escaneo ⇒ canjea el vale:

redeemed = min(subtotal, voucher)

change = max(voucher - subtotal, 0)

Marca buyer.paid = True.

Eventos que registra:

scan (producto escaneado)

redeem (canje + cambio)

sim/world.py — World (orquestador)

Mantiene WorldState y bandera finished.

reiniciar() coloca:

comprador en entrance,

cajero en su caja,

setea vale y algoritmo.

paso(n):

incrementa step

ejecuta buyer_agent.paso()

ejecuta cashier_agent.paso()

si pagó y llegó a exit ⇒ finished=True

a_dict() devuelve el estado completo para el frontend.

bitacora.py

write_event() agrega líneas JSON a data/bitacora.jsonl

Variable opcional: BITACORA_PATH para cambiar la ruta.

🔁 Flujo general de la simulación
sequenceDiagram
  participant UI as Frontend (Canvas)
  participant API as FastAPI
  participant W as World
  participant B as BuyerAgent
  participant C as CashierAgent

  UI->>API: POST /api/reset?voucher&algo
  API->>W: reiniciar()
  W-->>API: state (dict)
  API-->>UI: state

  loop cada tick
    UI->>API: POST /api/step?n=1
    API->>W: paso()
    W->>B: paso(world_state)
    W->>C: paso(world_state)
    W-->>API: state (dict)
    API-->>UI: state
  end

🌐 API (Backend)

Base URL típica: http://localhost:8000

GET /api/state → estado completo (mapa + agentes + logs)

POST /api/reset?voucher=120&algo=astar&cashier_register=R1 → reinicia simulación

POST /api/step?n=1 → avanza N ticks

GET /api/branches → lista mapas disponibles en /data

GET /health → salud del backend

Nota: en el frontend incluido se usa GET /api/map. Si tu backend expone /api/state, puedes:

cambiar el frontend a /api/state, o

crear un alias /api/map en backend que devuelva lo mismo.

▶️ Instalación y ejecución
1) Backend (FastAPI)
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

2) Frontend (Canvas)

Recomendado usar servidor estático:

Opción A: VSCode Live Server

Clic derecho en frontend/index.html → “Open with Live Server”

Opción B: Python

cd frontend
python -m http.server 5173


Abrir: http://localhost:5173

🏬 Cómo añadir una nueva sucursal (mapa)

Crea un nuevo archivo: data/mi_sucursal.json

Respeta la estructura base (ejemplo en supermarket_cbba_v1.json):

meta, grid, entrance, exit, shelves, registers, sections, products

Reinicia backend y consulta:

GET /api/branches
