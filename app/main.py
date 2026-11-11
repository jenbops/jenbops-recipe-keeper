from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import repo
from .db import get_conn
from .ui import router as ui_router

app = FastAPI(title="Recipe Keeper")


@app.middleware("http")
async def security(request: Request, call_next):
    # Cross-site request forgery (CSRF) defense: browsers attach an Origin header to
    # form posts. If it names a different site than this one, refuse the request.
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host"):
            return JSONResponse(
                {"detail": "Cross-site request blocked"}, status_code=403
            )
    response = await call_next(request)
    # Security headers: stop content-type guessing, block framing, limit referrer info
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


app.include_router(ui_router)  # adds the web pages from ui.py


class RecipeIn(BaseModel):
    title: str
    ingredients: str = ""
    steps: str = ""
    source_url: str | None = None
    notes: str | None = None
    tags: list[str] = []


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    with get_conn() as conn:
        row = conn.execute("select 1 as ok").fetchone()
    return {"db": "ok" if row["ok"] == 1 else "error"}


@app.post("/recipes", status_code=201)
def create_recipe(r: RecipeIn):
    return {"id": repo.create_recipe(r.model_dump())}


@app.get("/recipes")
def list_recipes(q: str | None = None, tag: list[str] = Query(default=[])):
    return repo.list_recipes(q, tag)


@app.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: int):
    row = repo.get_recipe(recipe_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return row


@app.put("/recipes/{recipe_id}")
def update_recipe(recipe_id: int, r: RecipeIn):
    if not repo.update_recipe(recipe_id, r.model_dump()):
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {"id": recipe_id}


@app.delete("/recipes/{recipe_id}", status_code=204)
def delete_recipe(recipe_id: int):
    if not repo.delete_recipe(recipe_id):
        raise HTTPException(status_code=404, detail="Recipe not found")


@app.get("/tags")
def list_tags():
    return repo.list_tags()