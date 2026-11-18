def test_default_theme_is_copper(client):
    assert 'data-theme="copper"' in client.get("/").text


def test_choosing_a_theme_sets_a_cookie_and_applies_it(client):
    r = client.post("/theme", data={"theme": "navy", "next": "/shopping"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/shopping"
    assert 'data-theme="navy"' in client.get("/").text


def test_unknown_theme_is_rejected(client):
    r = client.post("/theme", data={"theme": "<script>"}, follow_redirects=False)
    assert r.status_code == 400


def test_tampered_cookie_falls_back_to_default(client):
    client.cookies.set("theme", '"><script>alert(1)</script>')
    page = client.get("/").text
    assert 'data-theme="copper"' in page
    assert "<script>alert(1)" not in page


def test_redirect_never_leaves_this_site(client):
    r = client.post("/theme", data={"theme": "navy", "next": "https://evil.example"}, follow_redirects=False)
    assert r.headers["location"] == "/"


def test_shopping_page_gets_the_theme_too(client):
    client.post("/theme", data={"theme": "pearl", "next": "/"}, follow_redirects=False)
    assert 'data-theme="pearl"' in client.get("/shopping").text