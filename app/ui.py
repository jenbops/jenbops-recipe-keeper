from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from .scaling import scale_rows
from .themes import THEMES, DEFAULT, theme_context

from . import repo

router = APIRouter()
templates = Jinja2Templates(
    directory=Path(__file__).parent / "templates",
    context_processors=[theme_context],
)

def _whole_number(text: str, label: str, minimum: int, maximum: int):
    # form boxes arrive as text: "" -> no value, "15" -> 15, anything else -> error
    text = text.strip()
    if not text:
        return None
    try:
        value = int(text)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"{label} must be a whole number")
    if not minimum <= value <= maximum:
        raise HTTPException(
            status_code=422, detail=f"{label} must be between {minimum} and {maximum}"
        )
    return value


def _data(title, ingredients, steps, source_url, notes, tags,
          servings, prep_minutes, cook_minutes) -> dict:
    # turns raw form text into the dict that repo.py expects
    if not title.strip():
        raise HTTPException(status_code=422, detail="Title is required")
    return {
        "title": title.strip(),
        "ingredients": ingredients,
        "steps": steps,
        "source_url": source_url.strip() or None,  # empty box -> no value
        "notes": notes.strip() or None,
        "tags": tags.split(","),  # "a, b" -> ["a", " b"]; repo.py trims and lowercases
        "servings": _whole_number(servings, "Servings", 1, 1000),
        "prep_minutes": _whole_number(prep_minutes, "Prep time", 0, 10000),
        "cook_minutes": _whole_number(cook_minutes, "Cook time", 0, 10000),
    }
def _lines(recipe, servings=None):
    # base = what the recipe was written for; target = what the person asked for
    base = recipe["servings"]
    target = servings or base
    if not base or not target:
        base = target = 1  # no original servings known: show the lines unchanged
    return scale_rows(recipe["ingredient_rows"], base, target)

@router.get("/", response_class=HTMLResponse)
def home(request: Request, q: str = "", tag: list[str] = Query(default=[])):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "recipes": repo.list_recipes(q, tag),
            "all_tags": repo.list_tags(),
            "q": q,
            "selected": tag,
        },
    )


@router.get("/partials/list", response_class=HTMLResponse)
def list_partial(request: Request, q: str = "", tag: list[str] = Query(default=[])):
    return templates.TemplateResponse(
        request, "_list.html", {"recipes": repo.list_recipes(q, tag)}
    )


# NOTE: /r/new must come BEFORE /r/{recipe_id}, or "new" would be read as an id
@router.get("/r/new", response_class=HTMLResponse)
def new_form(request: Request):
    return templates.TemplateResponse(
        request, "form.html", {"r": None, "all_tags": repo.list_tags()}
    )


@router.post("/r/new")
def create(
    title: str = Form(...),
    ingredients: str = Form(""),
    steps: str = Form(""),
    source_url: str = Form(""),
    notes: str = Form(""),
    tags: str = Form(""),
    servings: str = Form(""),
    prep_minutes: str = Form(""),
    cook_minutes: str = Form(""),
):
    data = _data(title, ingredients, steps, source_url, notes, tags,
                 servings, prep_minutes, cook_minutes)
    rid = repo.create_recipe(data)
    return RedirectResponse(f"/r/{rid}", status_code=303)


@router.get("/r/{recipe_id}", response_class=HTMLResponse)
def view_recipe(request: Request, recipe_id: int):
    recipe = repo.get_recipe(recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return templates.TemplateResponse(
        request, "view.html", {"r": recipe, "lines": _lines(recipe)}
    )


@router.get("/r/{recipe_id}/ingredients", response_class=HTMLResponse)
def ingredients_partial(
    request: Request, recipe_id: int, servings: int = Query(ge=1, le=1000)
):
    # returns just the ingredient list (a fragment of HTML), for htmx to swap in
    recipe = repo.get_recipe(recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return templates.TemplateResponse(
        request, "_ingredients.html", {"lines": _lines(recipe, servings)}
    )

@router.get("/r/{recipe_id}/edit", response_class=HTMLResponse)
def edit_form(request: Request, recipe_id: int):
    recipe = repo.get_recipe(recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return templates.TemplateResponse(
        request, "form.html", {"r": recipe, "all_tags": repo.list_tags()}
    )


@router.post("/r/{recipe_id}/edit")
def update(
    recipe_id: int,
    title: str = Form(...),
    ingredients: str = Form(""),
    steps: str = Form(""),
    source_url: str = Form(""),
    notes: str = Form(""),
    tags: str = Form(""),
    servings: str = Form(""),
    prep_minutes: str = Form(""),
    cook_minutes: str = Form(""),
):
    data = _data(title, ingredients, steps, source_url, notes, tags,
                 servings, prep_minutes, cook_minutes)
    if not repo.update_recipe(recipe_id, data):
        raise HTTPException(status_code=404, detail="Recipe not found")
    return RedirectResponse(f"/r/{recipe_id}", status_code=303)


@router.post("/r/{recipe_id}/delete")
def delete(recipe_id: int):
    if not repo.delete_recipe(recipe_id):
        raise HTTPException(status_code=404, detail="Recipe not found")
    return RedirectResponse("/", status_code=303)

@router.post("/theme")
def set_theme(theme: str = Form(...), next: str = Form("/")):
    if theme not in THEMES:
        raise HTTPException(status_code=400, detail="Unknown theme")
    # only go back to a page on this site, never to another website
    target = next if next.startswith("/") and not next.startswith("//") else "/"
    response = RedirectResponse(target, status_code=303)
    response.set_cookie("theme", theme, max_age=60 * 60 * 24 * 365, samesite="lax", httponly=True)
    return response