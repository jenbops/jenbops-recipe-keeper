import pytest

from app.scaling import item_text, pluralize_name, scale_rows, singularize_name


@pytest.mark.parametrize(
    "name, plural",
    [
        ("onion", "onions"),
        ("tomato", "tomatoes"),
        ("berry", "berries"),
        ("peach", "peaches"),
        ("egg", "eggs"),
        ("garlic clove", "garlic cloves"),
        ("chopped onion", "chopped onions"),
        ("bay leaf", "bay leaves"),
        ("eggs", "eggs"),  # already plural
        ("salt", "salt"),  # measured, not counted
        ("flour", "flour"),
        ("pork chops (7 ounces each)", "pork chops (7 ounces each)"),  # don't touch odd endings
    ],
)
def test_pluralize_name(name, plural):
    assert pluralize_name(name) == plural


@pytest.mark.parametrize(
    "name, singular",
    [
        ("eggs", "egg"),
        ("tomatoes", "tomato"),
        ("berries", "berry"),
        ("peaches", "peach"),
        ("garlic cloves", "garlic clove"),
        ("bay leaves", "bay leaf"),
        ("cookies", "cookie"),
        ("hummus", "hummus"),
        ("asparagus", "asparagus"),
        ("onion", "onion"),
    ],
)
def test_singularize_name(name, singular):
    assert singularize_name(name) == singular


ONION = [{"quantity": 1, "unit": None, "name": "onion", "note": None, "original_text": "1 onion"}]
EGGS = [{"quantity": 2, "unit": None, "name": "eggs", "note": None, "original_text": "2 eggs"}]
CHOPPED = [{"quantity": 2, "unit": "cup", "name": "chopped onion", "note": None,
            "original_text": "2 cups chopped onion"}]


def test_doubling_pluralizes_counted_items():
    assert scale_rows(ONION, 2, 4)[0]["text"] == "2 onions"


def test_halving_makes_counted_items_singular():
    assert scale_rows(EGGS, 4, 2)[0]["text"] == "1 egg"


def test_measured_items_keep_their_name():
    assert scale_rows(CHOPPED, 2, 4)[0]["text"] == "4 cups chopped onion"


def test_shopping_text_handles_counted_items_and_slices():
    assert item_text(2, None, "onion") == "2 onions"
    assert item_text(1, None, "garlic cloves") == "1 garlic clove"
    assert item_text(0.5, None, "onion") == "1/2 onion"
    assert item_text(2, "slice", "bread") == "2 slices bread"