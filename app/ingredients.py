import re
from fractions import Fraction

# turn "½" into text the code understands
UNICODE_FRACTIONS = {"½": " 1/2", "¼": " 1/4", "¾": " 3/4", "⅓": " 1/3", "⅔": " 2/3", "⅛": " 1/8"}

# every spelling we recognize -> one standard unit name
UNITS = {
    "cup": "cup", "cups": "cup", "c": "cup",
    "tablespoon": "tbsp", "tablespoons": "tbsp", "tbsp": "tbsp", "tbsps": "tbsp", "tbs": "tbsp",
    "teaspoon": "tsp", "teaspoons": "tsp", "tsp": "tsp", "tsps": "tsp",
    "ounce": "oz", "ounces": "oz", "oz": "oz",
    "pound": "lb", "pounds": "lb", "lb": "lb", "lbs": "lb",
    "gram": "g", "grams": "g", "g": "g",
    "kilogram": "kg", "kilograms": "kg", "kg": "kg",
    "milliliter": "ml", "milliliters": "ml", "ml": "ml",
    "liter": "l", "liters": "l", "l": "l",
    "clove": "clove", "cloves": "clove",
    "can": "can", "cans": "can",
    "pinch": "pinch", "pinches": "pinch", 
    "slice": "slice", "slices": "slice",
}

# a number at the start: "1 1/2", "3/4", "2.5", or "2"
QUANTITY = re.compile(r"^\s*(\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)\s*")
# "2-3" or "2 to 3" at the start
RANGE = re.compile(r"^\s*\d+(?:\.\d+)?\s*(?:-|–|to)\s*\d")


def _whole_line(line: str) -> dict:
    # fallback: keep the text as typed, with no quantity, so it is never scaled wrongly
    text = line.strip()
    return {"quantity": None, "unit": None, "name": text, "note": None, "original_text": line}


def parse_line(line: str) -> dict:
    text = line.strip()
    for symbol, replacement in UNICODE_FRACTIONS.items():
        text = text.replace(symbol, replacement)
    text = re.sub(r"\s+", " ", text).strip()
        # "1-1/2" is a mixed fraction written with a hyphen, not a range: make it "1 1/2"
    text = re.sub(r"^(\d+)[-–](\d+/\d+)", r"\1 \2", text)

    if RANGE.match(text):
        return _whole_line(line)
    match = QUANTITY.match(text)
    if not match:
        return _whole_line(line)

    quantity = float(sum(Fraction(part) for part in match.group(1).split()))
    rest = text[match.end():]

    # everything after the first comma is a note ("garlic, minced")
    name_part, _, note = rest.partition(",")
    words = name_part.strip().split(" ", 1)
    unit = UNITS.get(words[0].lower().rstrip("."))
    name = (words[1] if len(words) > 1 else "") if unit else name_part.strip()
    if name.lower().startswith("of "):
        name = name[3:]
    name = name.strip()
    if not name:
        return _whole_line(line)

    return {
        "quantity": round(quantity, 3),
        "unit": unit,
        "name": name,
        "note": note.strip() or None,
        "original_text": line,
    }


def parse_ingredients(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        if line.strip():  # skip blank lines
            row = parse_line(line)
            row["position"] = len(rows) + 1
            rows.append(row)
    return rows