from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from . import shopping_repo
from .ui import _whole_number

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def _context() -> dict:
    items = shopping_repo.list_items()
    return {
        "to_buy": [i for i in items if not i["have"]],
        "have": [i for i in items if i["have"]],
    }


@router.get("/shopping", response_class=HTMLResponse)
def shopping_page(request: Request):
    return templates.TemplateResponse(request, "shopping.html", _context())


@router.post("/shopping/add/{recipe_id}")
def add_to_list(recipe_id: int, servings: str = Form("")):
    value = _whole_number(servings, "Servings", 1, 1000)
    if not shopping_repo.add_recipe(recipe_id, value):
        raise HTTPException(status_code=404, detail="Recipe not found")
    return RedirectResponse("/shopping", status_code=303)


@router.post("/shopping/clear")
def clear_list():
    shopping_repo.clear_all()
    return RedirectResponse("/shopping", status_code=303)


@router.post("/shopping/{item_id}/toggle", response_class=HTMLResponse)
def toggle(request: Request, item_id: int):
    if not shopping_repo.toggle_item(item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return templates.TemplateResponse(request, "_shopping_list.html", _context())


@router.post("/shopping/{item_id}/delete", response_class=HTMLResponse)
def delete(request: Request, item_id: int):
    if not shopping_repo.delete_item(item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return templates.TemplateResponse(request, "_shopping_list.html", _context())