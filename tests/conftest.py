import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import psycopg
import pytest
from fastapi.testclient import TestClient

ADMIN_URL = os.environ["TEST_DATABASE_ADMIN_URL"]  # the maintenance database, not recipes
TEST_DB = "recipes_test"
SCHEMA = Path(__file__).resolve().parent.parent / "db" / "schema.sql"


def _url_for(dbname: str) -> str:
    parts = urlparse(ADMIN_URL)
    return urlunparse(parts._replace(path=f"/{dbname}"))


@pytest.fixture(scope="session", autouse=True)
def test_database():
    """Create a fresh throwaway database for the whole test run, delete it afterwards."""
    assert TEST_DB != "recipes"  # safety: never the real database
    with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
        admin.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
        admin.execute(f"CREATE DATABASE {TEST_DB}")
    url = _url_for(TEST_DB)
    with psycopg.connect(url) as conn:
        conn.execute(SCHEMA.read_text())
    os.environ["DATABASE_URL"] = url  # the app reads this on every database call
    yield url
    with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
        admin.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")


@pytest.fixture(autouse=True)
def clean_tables(test_database):
    """Empty the tables before every test so tests can't affect each other."""
    assert os.environ["DATABASE_URL"].endswith("/" + TEST_DB)  # second safety check
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute("TRUNCATE recipes, tags, shopping_items RESTART IDENTITY CASCADE")


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)


def make_recipe(client, **overrides) -> int:
    """Helper: create a recipe through the JSON interface and return its id."""
    body = {
        "title": "Veggie Chili",
        "ingredients": "beans\ntomatoes",
        "steps": "simmer 30 minutes",
        "tags": ["Vegetarian", "30-min"],
    }
    body.update(overrides)
    response = client.post("/recipes", json=body)
    assert response.status_code == 201
    return response.json()["id"]