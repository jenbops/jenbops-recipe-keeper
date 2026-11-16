from app.scaling import format_quantity, scale_rows
from conftest import make_recipe

ROWS = [
    {"quantity": 2, "unit": "cup", "name": "flour", "note": None, "original_text": "2 cups flour"},
    {"quantity": 1, "unit": "clove", "name": "garlic", "note": "minced",
     "original_text": "1 clove garlic, minced"},
    {"quantity": None, "unit": None, "name": "salt to taste", "note": None,
     "original_text": "salt to taste"},
]


def texts(lines):
    return [line["text"] for line in lines]


# --- friendly number formatting ---
def test_whole_numbers_have_no_decimals():
    assert format_quantity(2.0) == "2"


def test_common_fractions():
    assert format_quantity(0.5) == "1/2"
    assert format_quantity(0.25) == "1/4"
    assert format_quantity(1.5) == "1 1/2"
    assert format_quantity(2.75) == "2 3/4"
    assert format_quantity(0.333) == "1/3"
    assert format_quantity(0.667) == "2/3"


def test_odd_amounts_fall_back_to_decimals():
    assert format_quantity(0.07) == "0.07"


# --- scaling the lines ---
def test_same_servings_shows_exactly_what_you_typed():
    assert texts(scale_rows(ROWS, 4, 4)) == [
        "2 cups flour", "1 clove garlic, minced", "salt to taste",
    ]


def test_doubling():
    assert texts(scale_rows(ROWS, 4, 8)) == [
        "4 cups flour", "2 cloves garlic, minced", "salt to taste",
    ]


def test_halving():
    assert texts(scale_rows(ROWS, 4, 2)) == [
        "1 cup flour", "1/2 clove garlic, minced", "salt to taste",
    ]


def test_lines_without_a_quantity_are_flagged_unscaled():
    flags = [line["scaled"] for line in scale_rows(ROWS, 4, 8)]
    assert flags == [True, True, False]


# --- the page fragment and the recipe page ---
def test_fragment_doubles_amounts(client):
    rid = make_recipe(client, servings=4, ingredients="2 cups flour\n3 eggs\nsalt to taste")
    html = client.get(f"/r/{rid}/ingredients", params={"servings": 8}).text
    assert "4 cups flour" in html
    assert "6 eggs" in html
    assert "salt to taste" in html


def test_scaling_never_changes_the_saved_recipe(client):
    rid = make_recipe(client, servings=4, ingredients="2 cups flour")
    client.get(f"/r/{rid}/ingredients", params={"servings": 12})
    saved = client.get(f"/recipes/{rid}").json()
    assert saved["servings"] == 4
    assert saved["ingredients"] == "2 cups flour"


def test_bad_servings_are_rejected(client):
    rid = make_recipe(client, servings=4)
    for bad in ("0", "-2", "abc", "99999"):
        assert client.get(f"/r/{rid}/ingredients", params={"servings": bad}).status_code == 422


def test_recipe_without_servings_shows_list_but_no_scaler(client):
    rid = make_recipe(client, ingredients="2 cups flour")
    page = client.get(f"/r/{rid}").text
    assert "2 cups flour" in page
    assert 'name="servings"' not in page


def test_fragment_for_recipe_without_servings_is_unchanged(client):
    rid = make_recipe(client, ingredients="2 cups flour")
    html = client.get(f"/r/{rid}/ingredients", params={"servings": 8}).text
    assert "2 cups flour" in html


def test_recipe_page_has_the_scaler_when_servings_are_set(client):
    rid = make_recipe(client, servings=4, ingredients="2 cups flour")
    page = client.get(f"/r/{rid}").text
    assert f'hx-get="/r/{rid}/ingredients"' in page


def test_ingredient_html_is_escaped(client):
    rid = make_recipe(client, servings=2, ingredients="<script>alert(1)</script>")
    assert "<script>alert(1)</script>" not in client.get(f"/r/{rid}").text