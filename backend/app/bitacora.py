from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def _default_path() -> Path:
    # Guardar en /data para que quede fuera del código.
    # Se puede sobreescribir con BITACORA_PATH.
    p = os.getenv("BITACORA_PATH")
    if p:
        return Path(p)
    return Path(__file__).resolve().parents[2] / "data" / "bitacora.jsonl"


def write_event(event: Dict[str, Any]) -> None:
    """Escribe un evento en una bitácora JSONL (1 línea = 1 evento)."""
    try:
        path = _default_path()
        path.parent.mkdir(parents=True, exist_ok=True)

        enriched = dict(event)
        enriched.setdefault("ts", datetime.utcnow().isoformat() + "Z")

        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(enriched, ensure_ascii=False) + "\n")
    except Exception:
        # Nunca romper la simulación por un log.
        return
