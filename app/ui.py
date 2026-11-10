from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from . import repo

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def _data(title, ingredients, steps, source_url, notes, tags) -> dict:
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
    }


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
):
    rid = repo.create_recipe(_data(title, ingredients, steps, source_url, notes, tags))
    return RedirectResponse(f"/r/{rid}", status_code=303)


@router.get("/r/{recipe_id}", response_class=HTMLResponse)
def view_recipe(request: Request, recipe_id: int):
    recipe = repo.get_recipe(recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return templates.TemplateResponse(request, "view.html", {"r": recipe})


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
):
    data = _data(title, ingredients, steps, source_url, notes, tags)
    if not repo.update_recipe(recipe_id, data):
        raise HTTPException(status_code=404, detail="Recipe not found")
    return RedirectResponse(f"/r/{recipe_id}", status_code=303)


@router.post("/r/{recipe_id}/delete")
def delete(recipe_id: int):
    if not repo.delete_recipe(recipe_id):
        raise HTTPException(status_code=404, detail="Recipe not found")
    return RedirectResponse("/", status_code=303)