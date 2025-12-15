from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Set, Tuple

# Estructuras mínimas tipo STRIPS.
# Nota: en esta versión, los agentes usan planificación por metas + pathfinding,
# pero dejamos esta base para que luego puedas ampliar a un planificador STRIPS completo.


Predicate = str  # e.g., "At(buyer,1,2)"


@dataclass(frozen=True)
class Operator:
    name: str
    preconditions: Set[Predicate]
    add_effects: Set[Predicate]
    del_effects: Set[Predicate]

    # --- Alias en español (propiedades) ---
    @property
    def nombre(self) -> str:
        return self.name

    @property
    def precondiciones(self) -> Set[Predicate]:
        return self.preconditions

    @property
    def efectos_agregar(self) -> Set[Predicate]:
        return self.add_effects

    @property
    def efectos_eliminar(self) -> Set[Predicate]:
        return self.del_effects



@dataclass
class StripsState:
    predicates: Set[Predicate]

    # --- Métodos en español ---
    def cumple(self, p: Predicate) -> bool:
        """True si el predicado está presente en el estado."""
        return self.holds(p)

    def aplicar(self, op: Operator) -> "StripsState":
        """Aplica un operador (acción) y devuelve un nuevo estado."""
        return self.apply(op)


    def holds(self, p: Predicate) -> bool:
        return p in self.predicates

    def apply(self, op: Operator) -> "StripsState":
        if not op.preconditions.issubset(self.predicates):
            raise ValueError("Preconditions not satisfied")
        new_preds = set(self.predicates)
        new_preds.difference_update(op.del_effects)
        new_preds.update(op.add_effects)
        return StripsState(new_preds)
