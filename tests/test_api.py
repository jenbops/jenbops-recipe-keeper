from conftest import make_recipe


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/health/db").json() == {"db": "ok"}


def test_create_and_get_cleans_tags(client):
    rid = make_recipe(client, tags=["Vegetarian", " vegetarian ", "Lunch"])
    data = client.get(f"/recipes/{rid}").json()
    assert data["title"] == "Veggie Chili"
    assert data["tags"] == ["lunch", "vegetarian"]  # lowercased, trimmed, de-duplicated


def test_keyword_search(client):
    make_recipe(client)
    make_recipe(client, title="BLT", ingredients="bacon", steps="toast", tags=["sandwich"])
    found = client.get("/recipes", params={"q": "chili"}).json()
    assert [r["title"] for r in found] == ["Veggie Chili"]


def test_tag_filter_requires_all_tags(client):
    make_recipe(client, title="A", tags=["x", "y"])
    make_recipe(client, title="B", tags=["x"])
    both = client.get("/recipes", params=[("tag", "x"), ("tag", "y")]).json()
    assert [r["title"] for r in both] == ["A"]
    one = client.get("/recipes", params={"tag": "x"}).json()
    assert {r["title"] for r in one} == {"A", "B"}


def test_update_replaces_tags(client):
    rid = make_recipe(client, tags=["old"])
    response = client.put(f"/recipes/{rid}", json={"title": "New", "tags": ["fresh"]})
    assert response.status_code == 200
    data = client.get(f"/recipes/{rid}").json()
    assert data["title"] == "New"
    assert data["tags"] == ["fresh"]


def test_delete_removes_recipe_but_keeps_tag(client):
    rid = make_recipe(client, tags=["keepme"])
    assert client.delete(f"/recipes/{rid}").status_code == 204
    assert client.get(f"/recipes/{rid}").status_code == 404
    tags = client.get("/tags").json()
    assert [t["name"] for t in tags] == ["keepme"]
    assert tags[0]["recipes"] == 0


def test_missing_recipe_returns_404(client):
    assert client.get("/recipes/9999").status_code == 404
    assert client.put("/recipes/9999", json={"title": "x"}).status_code == 404
    assert client.delete("/recipes/9999").status_code == 404