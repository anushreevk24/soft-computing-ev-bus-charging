"""Small data structures for the EV bus charging optimizer."""
from dataclasses import dataclass
from typing import List


@dataclass
class Bus:
    bus_id: str
    required_kwh: float
    charger_kw: float
    departure_slot: int
    initial_kwh: float = 0.0

    @property
    def energy_needed_kwh(self) -> float:
        needed = self.required_kwh - self.initial_kwh
        return needed if needed > 0 else 0.0


@dataclass
class ChargingProblem:
    buses: List[Bus]
    prices: List[float]
    transformer_limit_kw: float
    available_chargers: int
    slot_minutes: int
    start_label: str = "22:00"

    @property
    def slot_hours(self) -> float:
        return self.slot_minutes / 60.0

    @property
    def slots(self) -> int:
        return len(self.prices)
