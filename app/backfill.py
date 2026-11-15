from . import repo
from .db import get_conn


def backfill() -> int:
    """Read the typed ingredients of every recipe that has no rows yet."""
    with get_conn() as conn:
        todo = conn.execute(
            "SELECT id, ingredients FROM recipes r "
            "WHERE btrim(ingredients) <> '' "
            "AND NOT EXISTS (SELECT 1 FROM ingredients i WHERE i.recipe_id = r.id)"
        ).fetchall()
        for recipe in todo:
            repo.set_ingredients(conn, recipe["id"], recipe["ingredients"])
    return len(todo)


if __name__ == "__main__":
    print(f"Filled ingredient rows for {backfill()} recipes")