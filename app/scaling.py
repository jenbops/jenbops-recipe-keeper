import re
from fractions import Fraction

# singular unit -> plural, used when the amount is more than 1
PLURALS = {"cup": "cups", "clove": "cloves", "can": "cans", "pinch": "pinches", "slice": "slices"}

# things you measure rather than count: these never get an "s"
UNCOUNTABLE = {
    "salt", "flour", "sugar", "butter", "oil", "water", "rice", "milk", "honey",
    "cheese", "spinach", "garlic", "broth", "vinegar", "cream", "parsley",
    "cilantro", "bread",
}
IRREGULAR = {"leaf": "leaves", "loaf": "loaves", "half": "halves"}
NEEDS_ES = {"tomato", "potato"}
SINGULAR_EXCEPTIONS = {"cookies": "cookie", "brownies": "brownie", "pies": "pie"}
NEVER_SINGULAR = {"molasses", "chives", "oats"}


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


def _last_word(name: str):
    # only touch names that end in a plain word; "(7 ounces each)" is left alone
    head, _, last = name.rpartition(" ")
    if not re.fullmatch(r"[A-Za-z-]+", last):
        return None
    return head, last


def pluralize_name(name: str) -> str:
    """onion -> onions, tomato -> tomatoes, garlic clove -> garlic cloves."""
    parts = _last_word(name)
    if parts is None:
        return name
    head, last = parts
    lower = last.lower()
    if lower in UNCOUNTABLE or lower.endswith("s"):
        return name
    if lower in IRREGULAR:
        new = IRREGULAR[lower]
    elif re.search(r"[^aeiou]y$", lower):
        new = last[:-1] + "ies"
    elif lower in NEEDS_ES or lower.endswith(("ch", "sh", "x")):
        new = last + "es"
    else:
        new = last + "s"
    return f"{head} {new}".strip()


def singularize_name(name: str) -> str:
    """eggs -> egg, tomatoes -> tomato, garlic cloves -> garlic clove."""
    parts = _last_word(name)
    if parts is None:
        return name
    head, last = parts
    lower = last.lower()
    if lower in NEVER_SINGULAR or lower.endswith(("ss", "us", "is")) or not lower.endswith("s"):
        return name
    reverse = {plural: single for single, plural in IRREGULAR.items()}
    if lower in SINGULAR_EXCEPTIONS:
        new = SINGULAR_EXCEPTIONS[lower]
    elif lower in reverse:
        new = reverse[lower]
    elif lower.endswith("ies") and len(lower) > 4:
        new = last[:-3] + "y"
    elif lower.endswith("oes") or lower.endswith(("ches", "shes", "xes")):
        new = last[:-2]
    else:
        new = last[:-1]
    return f"{head} {new}".strip()


def _counted_name(name: str, unit, quantity: float) -> str:
    # "2 onions" / "1 onion": only for counted things, which have no unit
    if unit is not None:
        return name
    return pluralize_name(name) if quantity > 1 else singularize_name(name)


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
        name = _counted_name(row["name"], unit, q)
        if unit and q > 1:
            unit = PLURALS.get(unit, unit)
        parts = [format_quantity(q)]
        if unit:
            parts.append(unit)
        parts.append(name)
        text = " ".join(parts)
        if row["note"]:
            text += ", " + row["note"]
        lines.append({"text": text, "scaled": True})
    return lines


def item_text(quantity, unit, name) -> str:
    """Display text for a shopping item: 3.5, 'cup', 'flour' -> '3 1/2 cups flour'."""
    if quantity is None:
        return name
    q = float(quantity)
    name = _counted_name(name, unit, q)
    unit_text = PLURALS.get(unit, unit) if unit and q > 1 else unit
    return " ".join(part for part in (format_quantity(q), unit_text, name) if part)