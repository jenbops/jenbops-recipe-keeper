import pytest

from app.ingredients import parse_line, parse_ingredients


def check(line, quantity, unit, name, note=None):
    got = parse_line(line)
    assert got["quantity"] == pytest.approx(quantity) if quantity is not None else got["quantity"] is None
    assert got["unit"] == unit
    assert got["name"] == name
    assert got["note"] == note
    assert got["original_text"] == line


def test_whole_number_with_unit():
    check("2 cups flour", 2, "cup", "flour")


def test_mixed_fraction_and_unit_spelling():
    check("1 1/2 tablespoons olive oil", 1.5, "tbsp", "olive oil")


def test_unicode_fraction():
    check("½ tsp salt", 0.5, "tsp", "salt")


def test_count_without_unit():
    check("3 eggs", 3, None, "eggs")


def test_note_after_comma():
    check("2 cloves garlic, minced", 2, "clove", "garlic", "minced")


def test_optional_word_of():
    check("2 cups of flour", 2, "cup", "flour")


def test_no_quantity_is_kept_whole():
    check("salt to taste", None, None, "salt to taste")


def test_range_is_not_guessed():
    # "2-3 carrots" can't be scaled safely, so it is kept as typed
    check("2-3 carrots", None, None, "2-3 carrots")


def test_parse_ingredients_skips_blank_lines_and_numbers_positions():
    rows = parse_ingredients("2 cups flour\n\n  \n3 eggs\n")
    assert [r["position"] for r in rows] == [1, 2]
    assert [r["name"] for r in rows] == ["flour", "eggs"]

def test_hyphenated_mixed_fraction_is_not_a_range():
    check("1-1/2 teaspoons canola oil", 1.5, "tsp", "canola oil")


def test_en_dash_range_is_still_kept_whole():
    check("4–6 slices whole-wheat bread", None, None, "4–6 slices whole-wheat bread")    

def test_slice_is_a_unit():
    check("2 slices of bread", 2, "slice", "bread")
    check("1 slice bread", 1, "slice", "bread")    