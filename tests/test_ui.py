from conftest import make_recipe


def test_home_page_lists_recipes(client):
    make_recipe(client)
    page = client.get("/")
    assert page.status_code == 200
    assert "Veggie Chili" in page.text


def test_create_through_the_form(client):
    response = client.post(
        "/r/new", data={"title": "Form Soup", "tags": "soup, lunch"}, follow_redirects=False
    )
    assert response.status_code == 303
    page = client.get(response.headers["location"])
    assert "Form Soup" in page.text
    assert "lunch" in page.text


def test_html_in_titles_is_escaped(client):
    # cross-site scripting (XSS) check: a script in a title must be shown as text, not run
    rid = make_recipe(client, title="<script>alert(1)</script>")
    page = client.get(f"/r/{rid}")
    assert "<script>alert(1)</script>" not in page.text
    assert "&lt;script&gt;" in page.text


def test_javascript_links_are_not_rendered(client):
    rid = make_recipe(client, source_url="javascript:alert(1)")
    assert 'href="javascript:' not in client.get(f"/r/{rid}").text


def test_search_partial_filters_results(client):
    make_recipe(client)
    make_recipe(client, title="BLT", ingredients="bacon", steps="toast", tags=["sandwich"])
    html = client.get("/partials/list", params={"q": "chili"}).text
    assert "Veggie Chili" in html
    assert "BLT" not in html