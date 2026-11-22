THEMES = {
    "copper": "Copper & Teal",
    "sage": "Sage & Pearl",
    "navy": "Navy & Gold",
    "orchard": "Orchard",
    "raspberry": "Raspberry",
    "pearl": "Pearl",
}
DEFAULT = "copper"


def theme_from_request(request) -> str:
    """The saved theme, or the default if the cookie is missing or not on the list."""
    value = request.cookies.get("theme", DEFAULT)
    return value if value in THEMES else DEFAULT


def theme_context(request) -> dict:
    """Extra values every template can use."""
    return {"theme": theme_from_request(request), "themes": THEMES}