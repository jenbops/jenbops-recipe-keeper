import os
from pathlib import Path

import psycopg
from conftest import make_recipe

MIGRATION = (
    Path(__file__).resolve().parent.parent
    / "db" / "migrations" / "001_add_times_and_servings.sql"
)


def test_new_fields_round_trip(client):
    rid = make_recipe(client, servings=4, prep_minutes=15, cook_minutes=30)
    data = client.get(f"/recipes/{rid}").json()
    assert data["servings"] == 4
    assert data["prep_minutes"] == 15
    assert data["cook_minutes"] == 30


def test_new_fields_are_optional(client):
    # old-style recipes (and your existing ones) have no times; that must stay valid
    rid = make_recipe(client)
    data = client.get(f"/recipes/{rid}").json()
    assert data["servings"] is None
    assert data["prep_minutes"] is None
    assert data["cook_minutes"] is None


def test_update_changes_the_new_fields(client):
    rid = make_recipe(client)
    response = client.put(
        f"/recipes/{rid}", json={"title": "Veggie Chili", "servings": 6, "cook_minutes": 45}
    )
    assert response.status_code == 200
    data = client.get(f"/recipes/{rid}").json()
    assert data["servings"] == 6
    assert data["cook_minutes"] == 45


def test_bad_values_are_rejected(client):
    for bad in ({"servings": 0}, {"prep_minutes": -5}, {"cook_minutes": -1}):
        body = {"title": "Bad", **bad}
        assert client.post("/recipes", json=body).status_code == 422


def test_form_saves_and_shows_times(client):
    response = client.post(
        "/r/new",
        data={"title": "Timed Soup", "servings": "4", "prep_minutes": "15", "cook_minutes": "30"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    page = client.get(response.headers["location"]).text
    assert "Serves 4" in page
    assert "Prep: 15 min" in page
    assert "Cook: 30 min" in page


def test_form_allows_blank_fields(client):
    response = client.post(
        "/r/new",
        data={"title": "Blank Soup", "servings": "", "prep_minutes": "", "cook_minutes": ""},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_migration_is_safe_to_run_twice(test_database):
    # "IF NOT EXISTS" means rerunning the migration changes nothing and never errors
    sql = MIGRATION.read_text()
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute(sql)
        conn.execute(sql)