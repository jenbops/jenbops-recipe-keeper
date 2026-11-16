from fractions import Fraction

# singular unit -> plural, used when the amount is more than 1
PLURALS = {"cup": "cups", "clove": "cloves", "can": "cans", "pinch": "pinches"}


def format_quantity(q) -> str:
    """0.5 -> '1/2', 1.5 -> '1 1/2', 2.0 -> '2'. Odd amounts become decimals."""
    q = float(q)
    if q <= 0:
        return "0"
    # try the denominators cooks actually use; min() keeps the first (simplest) on a tie
    best = min(
        (Fraction(round(q * d), d) for d in (1, 2, 3, 4, 8)),
        key=lambda f: abs(f - Fraction(q)),
    )
    if best == 0 or abs(float(best) - q) / q > 0.05:  # more than 5% off: show a decimal
        return f"{q:.2f}".rstrip("0").rstrip(".")
    whole, rest = divmod(best.numerator, best.denominator)
    if rest == 0:
        return str(whole)
    part = f"{rest}/{best.denominator}"
    return f"{whole} {part}" if whole else part


def scale_rows(rows, servings_from: int, servings_to: int) -> list[dict]:
    """Return display lines [{'text': ..., 'scaled': bool}] for the new serving count."""
    factor = servings_to / servings_from
    lines = []
    for row in rows:
        # no amount, or no change requested: show exactly what was typed
        if row["quantity"] is None or factor == 1:
            lines.append({"text": row["original_text"], "scaled": False})
            continue
        q = float(row["quantity"]) * factor
        unit = row["unit"]
        if unit and q > 1:
            unit = PLURALS.get(unit, unit)
        parts = [format_quantity(q)]
        if unit:
            parts.append(unit)
        parts.append(row["name"])
        text = " ".join(parts)
        if row["note"]:
            text += ", " + row["note"]
        lines.append({"text": text, "scaled": True})
    return lines