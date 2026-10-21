"""Hand-coded fuzzy inference for slot attractiveness; no fuzzy library used."""
from typing import Dict


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return low if value < low else high if value > high else value


def triangular(x: float, left: float, peak: float, right: float) -> float:
    """Triangular membership function."""
    if x < left or x > right:
        return 0.0
    if x == peak:
        return 1.0
    if x < peak:
        return (x - left) / (peak - left) if peak != left else 1.0
    return (right - x) / (right - peak) if right != peak else 1.0


def price_memberships(price: float, minimum: float, maximum: float) -> Dict[str, float]:
    span = maximum - minimum
    if span <= 1e-12:
        return {"low": 1.0, "medium": 0.0, "high": 0.0}
    x = (price - minimum) / span
    return {
        "low": triangular(x, -0.5, 0.0, 0.55),
        "medium": triangular(x, 0.15, 0.5, 0.85),
        "high": triangular(x, 0.45, 1.0, 1.5),
    }


def urgency_memberships(slots_left: int, max_slots: int) -> Dict[str, float]:
    """Urgency is high when few slots remain before departure."""
    if max_slots <= 1:
        x = 1.0
    else:
        x = 1.0 - clamp((slots_left - 1) / (max_slots - 1))
    return {
        "low": triangular(x, -0.3, 0.0, 0.55),
        "medium": triangular(x, 0.2, 0.5, 0.8),
        "high": triangular(x, 0.45, 1.0, 1.4),
    }


def slot_attractiveness(price: float, slots_left: int, max_slots: int,
                        minimum_price: float, maximum_price: float) -> float:
    """
    Mamdani-style compact rule system with weighted singleton outputs.
    Larger score means more attractive for charging.
    Rules:
      low price + any urgency -> very attractive
      medium price + high urgency -> attractive
      high price + high urgency -> moderate (must still meet deadline)
      high price + low urgency -> unattractive
      medium price + low/medium urgency -> moderate
    """
    p = price_memberships(price, minimum_price, maximum_price)
    u = urgency_memberships(slots_left, max_slots)
    rules = [
        (min(p["low"], max(u.values())), 1.00),
        (min(p["medium"], u["high"]), 0.78),
        (min(p["high"], u["high"]), 0.48),
        (min(p["medium"], max(u["low"], u["medium"])), 0.55),
        (min(p["high"], max(u["low"], u["medium"])), 0.12),
        (min(p["low"], u["high"]), 1.00),
    ]
    denominator = sum(strength for strength, _ in rules)
    if denominator <= 1e-12:
        # Transparent fallback if the membership functions leave a gap.
        normalized_price = 0.5 if maximum_price == minimum_price else (
            (price - minimum_price) / (maximum_price - minimum_price))
        return 1.0 - clamp(normalized_price) + 0.25 * clamp(1.0 - slots_left / max(1, max_slots))
    return sum(strength * output for strength, output in rules) / denominator
