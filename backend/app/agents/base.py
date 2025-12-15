from __future__ import annotations

from typing import Protocol

from ..models import WorldState


class Agent(Protocol):
    """Protocolo base (interfaz) que deben cumplir los agentes del simulador."""

    # Nombre/identificador del agente (para logs, debug, etc.)
    identificador: str

    # Alias de compatibilidad (inglés)
    id: str

    def paso(self, mundo: WorldState) -> None:
        """Ejecuta un tick (paso) del agente sobre el estado del mundo."""
        ...

    # Alias de compatibilidad (inglés)
    def step(self, world: WorldState) -> None:
        ...
