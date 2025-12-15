from __future__ import annotations

from typing import Optional

from ..models import WorldState


def find_register_by_queue_spot(world: WorldState, pos) -> Optional[str]:
    """Devuelve el id de la caja si `pos` coincide con el queue_spot de alguna caja."""
    for rid, reg in world.map_data.registers.items():
        if reg.queue_spot == pos:
            return rid
    return None
