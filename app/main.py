from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from .db import get_conn

app = FastAPI(title="Recipe Keeper")


class RecipeIn(BaseModel):
    # Pydantic checks incoming data matches this shape, and rejects it otherwise
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
    with get_conn() as conn:  # commits when the block ends successfully
        rid = conn.execute(
            "INSERT INTO recipes (title, ingredients, steps, source_url, notes) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (r.title, r.ingredients, r.steps, r.source_url, r.notes),
        ).fetchone()["id"]
        # clean tags: trim spaces, lowercase, remove duplicates and blanks
        for name in {t.strip().lower() for t in r.tags if t.strip()}:
            tag_id = conn.execute(
                "INSERT INTO tags (name) VALUES (%s) "
                "ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id",
                (name,),
            ).fetchone()["id"]
            conn.execute(
                "INSERT INTO recipe_tags (recipe_id, tag_id) VALUES (%s, %s) "
                "ON CONFLICT DO NOTHING",
                (rid, tag_id),
            )
    return {"id": rid}


@app.get("/recipes")
def list_recipes(q: str | None = None, tag: list[str] = Query(default=[])):
    where, params = [], []
    if q:
        where.append("r.search_vector @@ websearch_to_tsquery('english', %s)")
        params.append(q)
    if tag:
        tags = [t.strip().lower() for t in tag]
        # recipe must have ALL requested tags
        where.append(
            "r.id IN (SELECT rt2.recipe_id FROM recipe_tags rt2 "
            "JOIN tags t2 ON t2.id = rt2.tag_id WHERE t2.name = ANY(%s) "
            "GROUP BY rt2.recipe_id HAVING count(*) = %s)"
        )
        params += [tags, len(tags)]
    sql = (
        "SELECT r.id, r.title, "
        "coalesce(array_agg(t.name ORDER BY t.name) FILTER (WHERE t.name IS NOT NULL), '{}') AS tags "
        "FROM recipes r "
        "LEFT JOIN recipe_tags rt ON rt.recipe_id = r.id "
        "LEFT JOIN tags t ON t.id = rt.tag_id "
        + ("WHERE " + " AND ".join(where) + " " if where else "")
        + "GROUP BY r.id ORDER BY r.created_at DESC"
    )
    with get_conn() as conn:
        return conn.execute(sql, params).fetchall()


@app.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT r.id, r.title, r.ingredients, r.steps, r.source_url, r.notes, "
            "coalesce(array_agg(t.name ORDER BY t.name) FILTER (WHERE t.name IS NOT NULL), '{}') AS tags "
            "FROM recipes r "
            "LEFT JOIN recipe_tags rt ON rt.recipe_id = r.id "
            "LEFT JOIN tags t ON t.id = rt.tag_id "
            "WHERE r.id = %s GROUP BY r.id",
            (recipe_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return row


@app.delete("/recipes/{recipe_id}", status_code=204)
def delete_recipe(recipe_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "DELETE FROM recipes WHERE id = %s RETURNING id", (recipe_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Recipe not found")