from app.ingredients import parse_ingredients

PIE = """4 cups apple cider

crust:
 1-1/2 cups all-purpose flour
 1 tablespoon packed brown sugar
 1/2 teaspoon salt
 1/4 teaspoon ground nutmeg
 3/4 cup cold unsalted butter, cubed
 1/3 cup sour cream
 1 egg white, beaten

 filling:

 3/4 cup packed brown sugar
 1/4 cup all-purpose flour
 1 teaspoon ground cinnamon
 1/2 teaspoon salt
 1/4 teaspoon ground nutmeg
 1/8 teaspoon ground allspice
 2 large eggs, room temperature
 1 large egg yolk, room temperature
 1 teaspoon vanilla extract
 1/2 cup heavy whipping cream
 1/4 cup unsalted butter, melted

 cinnamon-sugar topping:

 3 tablespoons sugar
 1 teaspoon ground cinnamon
"""


def test_labels_are_not_ingredients():
    rows = parse_ingredients(PIE)
    assert len(rows) == 21
    assert not any(r["name"].rstrip().endswith(":") for r in rows)


def test_each_ingredient_knows_its_section():
    sections = [r["section"] for r in parse_ingredients(PIE)]
    assert sections == (
        [None] + ["Crust"] * 7 + ["Filling"] * 11 + ["Cinnamon-sugar topping"] * 2
    )


def test_positions_skip_the_labels():
    assert [r["position"] for r in parse_ingredients(PIE)] == list(range(1, 22))


def test_amounts_still_parse_inside_a_section():
    flour = parse_ingredients(PIE)[1]
    assert (flour["quantity"], flour["unit"], flour["name"]) == (1.5, "cup", "all-purpose flour")
    assert flour["section"] == "Crust"


def test_original_text_is_kept():
    assert parse_ingredients(PIE)[1]["original_text"] == " 1-1/2 cups all-purpose flour"


def test_a_colon_in_the_middle_is_not_a_label():
    rows = parse_ingredients("Salt: 1 tsp\n2 cups flour")
    assert len(rows) == 2
    assert [r["section"] for r in rows] == [None, None]


def test_no_labels_means_no_sections():
    rows = parse_ingredients("2 eggs\n1 cup milk")
    assert [r["section"] for r in rows] == [None, None]