"""Tolerance band logic for portfolio sleeves.

Based on Daryanani (2008) "Opportunistic Rebalancing" and Vanguard research.
Uses relative bands of 25% of target weight with a 2pp floor.
Soft band (watch) at 50% of full band, hard band (action) at 100%.
"""


def compute_bands(target_percent: float) -> tuple[float, float]:
    """Compute soft and hard bands for a given target weight.

    hard = max(2.0, 25% of target)
    soft = 50% of hard
    """
    hard = max(2.0, 0.25 * target_percent)
    soft = hard * 0.5
    return round(soft, 1), round(hard, 1)


def classify_drift(drift_pp: float, soft: float, hard: float) -> str:
    """Classify drift status.

    Returns: 'ok', 'watch', or 'action_needed'
    """
    abs_drift = abs(drift_pp)
    if abs_drift <= soft:
        return "ok"
    elif abs_drift <= hard:
        return "watch"
    else:
        return "action_needed"
