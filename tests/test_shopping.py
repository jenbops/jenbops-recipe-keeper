import os
from pathlib import Path

import psycopg
from app import shopping_repo
from conftest import make_recipe

MIGRATION = (
    Path(__file__).resolve().parent.parent / "db" / "migrations" / "003_add_shopping_items.sql"
)


def add(client, rid, **form):
    return client.post(f"/shopping/add/{rid}", data=form, follow_redirects=False)


def texts():
    return sorted(item["text"] for item in shopping_repo.list_items())


def test_adding_a_recipe_fills_the_list(client):
    rid = make_recipe(client, servings=4, ingredients="2 cups flour\n3 eggs")
    assert add(client, rid).status_code == 303
    assert texts() == ["2 cups flour", "3 eggs"]


def test_adding_with_new_servings_scales_the_amounts(client):
    rid = make_recipe(client, servings=4, ingredients="2 cups flour\n3 eggs")
    add(client, rid, servings="8")
    assert texts() == ["4 cups flour", "6 eggs"]


def test_same_ingredient_from_two_recipes_is_combined(client):
    a = make_recipe(client, title="A", servings=4, ingredients="2 cups flour")
    b = make_recipe(client, title="B", servings=4, ingredients="1 1/2 cups flour")
    add(client, a)
    add(client, b)
    assert texts() == ["3 1/2 cups flour"]


def test_different_units_stay_separate(client):
    rid = make_recipe(client, servings=2, ingredients="1 cup sugar\n2 tbsp sugar")
    add(client, rid)
    assert texts() == ["1 cup sugar", "2 tbsp sugar"]


def test_matching_ignores_capital_letters(client):
    a = make_recipe(client, title="A", servings=2, ingredients="2 cups Flour")
    b = make_recipe(client, title="B", servings=2, ingredients="1 cup flour")
    add(client, a)
    add(client, b)
    items = shopping_repo.list_items()
    assert len(items) == 1
    assert float(items[0]["quantity"]) == 3


def test_lines_without_an_amount_appear_once(client):
    a = make_recipe(client, title="A", ingredients="salt to taste")
    b = make_recipe(client, title="B", ingredients="salt to taste")
    add(client, a)
    add(client, b)
    assert texts() == ["salt to taste"]


def test_checking_an_item_moves_it_to_already_have(client):
    rid = make_recipe(client, servings=2, ingredients="2 cups flour")
    add(client, rid)
    item = shopping_repo.list_items()[0]
    response = client.post(f"/shopping/{item['id']}/toggle")
    assert response.status_code == 200
    assert "Already have" in response.text
    assert shopping_repo.list_items()[0]["have"] is True
    client.post(f"/shopping/{item['id']}/toggle")
    assert shopping_repo.list_items()[0]["have"] is False


def test_remove_one_item(client):
    rid = make_recipe(client, servings=2, ingredients="2 cups flour")
    add(client, rid)
    item = shopping_repo.list_items()[0]
    assert client.post(f"/shopping/{item['id']}/delete").status_code == 200
    assert shopping_repo.list_items() == []


def test_clear_the_whole_list(client):
    rid = make_recipe(client, servings=2, ingredients="2 cups flour\n3 eggs")
    add(client, rid)
    assert client.post("/shopping/clear", follow_redirects=False).status_code == 303
    assert shopping_repo.list_items() == []


def test_unknown_things_return_404(client):
    assert add(client, 9999).status_code == 404
    assert client.post("/shopping/9999/toggle").status_code == 404
    assert client.post("/shopping/9999/delete").status_code == 404


def test_bad_servings_are_rejected(client):
    rid = make_recipe(client, servings=2, ingredients="2 cups flour")
    assert add(client, rid, servings="abc").status_code == 422
    assert shopping_repo.list_items() == []


def test_empty_list_shows_a_friendly_message(client):
    assert "Your shopping list is empty" in client.get("/shopping").text


def test_recipe_page_has_an_add_button(client):
    rid = make_recipe(client, servings=2, ingredients="2 cups flour")
    assert f'action="/shopping/add/{rid}"' in client.get(f"/r/{rid}").text


def test_names_are_escaped_on_the_list_page(client):
    rid = make_recipe(client, servings=2, ingredients="2 cups <script>alert(1)</script>")
    add(client, rid)
    assert "<script>alert(1)</script>" not in client.get("/shopping").text


def test_migration_is_safe_to_run_twice(test_database):
    sql = MIGRATION.read_text()
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute(sql)
        conn.execute(sql)