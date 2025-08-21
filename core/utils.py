"""Assorted utility helpers."""


def fico_to_bucket(score):
    """Map a numeric credit score to the preset FICO buckets."""
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "760+"
    if s >= 760:
        return "760+"
    if s >= 720:
        return "720-759"
    return "<720"
