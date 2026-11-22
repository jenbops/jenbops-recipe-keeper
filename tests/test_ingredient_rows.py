import os
from pathlib import Path

import psycopg
from conftest import make_recipe

MIGRATION = (
    Path(__file__).resolve().parent.parent
    / "db" / "migrations" / "002_add_ingredients_table.sql"
)


def rows_for(client, rid):
    return client.get(f"/recipes/{rid}").json()["ingredient_rows"]


def test_rows_are_created_on_save(client):
    rid = make_recipe(client, ingredients="2 cups flour\n3 eggs")
    rows = rows_for(client, rid)
    assert [r["name"] for r in rows] == ["flour", "eggs"]
    assert rows[0]["quantity"] == 2 and rows[0]["unit"] == "cup"
    assert rows[1]["unit"] is None


def test_update_replaces_the_rows(client):
    rid = make_recipe(client, ingredients="2 cups flour")
    client.put(f"/recipes/{rid}", json={"title": "Veggie Chili", "ingredients": "1 tsp salt"})
    assert [r["name"] for r in rows_for(client, rid)] == ["salt"]


def test_original_text_column_is_untouched(client):
    typed = "½ tsp salt\nsalt to taste"
    rid = make_recipe(client, ingredients=typed)
    assert client.get(f"/recipes/{rid}").json()["ingredients"] == typed


def test_form_save_creates_rows(client):
    response = client.post(
        "/r/new", data={"title": "F", "ingredients": "2 cups flour"}, follow_redirects=False
    )
    rid = int(response.headers["location"].split("/")[-1])
    assert len(rows_for(client, rid)) == 1


def test_deleting_a_recipe_removes_its_rows(client):
    rid = make_recipe(client, ingredients="2 cups flour")
    client.delete(f"/recipes/{rid}")
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        assert conn.execute("SELECT count(*) FROM ingredients").fetchone()[0] == 0


def test_backfill_fills_recipes_saved_before_the_table_existed(client):
    from app.backfill import backfill

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        rid = conn.execute(
            "INSERT INTO recipes (title, ingredients, steps) "
            "VALUES ('Old', E'2 cups flour\\n3 eggs', '') RETURNING id"
        ).fetchone()[0]
    assert backfill() == 1
    assert [r["name"] for r in rows_for(client, rid)] == ["flour", "eggs"]
    assert backfill() == 0  # safe to run again: nothing left to do


def test_migration_is_safe_to_run_twice(test_database):
    sql = MIGRATION.read_text()
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute(sql)
        conn.execute(sql)

def test_sections_survive_save_and_reload(client):
    text = (
        "4 cups apple cider\n"
        "\n"
        "crust:\n"
        "1-1/2 cups all-purpose flour\n"
        "1 tsp salt\n"
        "\n"
        "filling:\n"
        "6 apples\n"
        "\n"
        "cinnamon-sugar topping:\n"
        "2 tbsp sugar"
    )
    rid = make_recipe(client, ingredients=text)
    rows = rows_for(client, rid)

    assert [r["name"] for r in rows] == [
        "apple cider", "all-purpose flour", "salt", "apples", "sugar",
    ]
    assert [r["section"] for r in rows] == [
        None, "Crust", "Crust", "Filling", "Cinnamon-sugar topping",
    ]
    assert [r["position"] for r in rows] == [1, 2, 3, 4, 5]        