"""Delivery estimates."""
import math


def eta_days(distance_km: float) -> int:
    """Whole days to deliver: one day per started 500 km, at least one."""
    if distance_km < 0:
        raise ValueError("distance must not be negative")
    return max(1, math.ceil(distance_km / 500))
