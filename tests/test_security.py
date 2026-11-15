from conftest import make_recipe


def test_foreign_origin_is_blocked(client):
    rid = make_recipe(client)
    response = client.post(f"/r/{rid}/delete", headers={"Origin": "https://evil.example"})
    assert response.status_code == 403  # cross-site request forgery (CSRF) defense
    assert client.get(f"/recipes/{rid}").status_code == 200  # recipe survived


def test_same_origin_is_allowed(client):
    rid = make_recipe(client)
    response = client.post(
        f"/r/{rid}/delete", headers={"Origin": "http://testserver"}, follow_redirects=False
    )
    assert response.status_code == 303


def test_security_headers_present(client):
    headers = client.get("/health").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"