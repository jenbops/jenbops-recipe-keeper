from . import repo
from .db import get_conn
from .scaling import item_text

# Insert the item; if the same name+unit already exists, add to it instead.
UPSERT = """
INSERT INTO shopping_items (name, unit, quantity, source_recipe_ids)
VALUES (%s, %s, %s, %s::bigint[])
ON CONFLICT (lower(name), coalesce(unit, '')) DO UPDATE SET
    quantity = CASE
        WHEN shopping_items.quantity IS NULL AND EXCLUDED.quantity IS NULL THEN NULL
        ELSE coalesce(shopping_items.quantity, 0) + coalesce(EXCLUDED.quantity, 0)
    END,
    source_recipe_ids = (
        SELECT array_agg(DISTINCT x)
        FROM unnest(shopping_items.source_recipe_ids || EXCLUDED.source_recipe_ids) AS x
    )
"""


def add_recipe(recipe_id: int, servings: int | None) -> bool:
    """Add every ingredient of a recipe, scaled to `servings`. False if no such recipe."""
    recipe = repo.get_recipe(recipe_id)
    if recipe is None:
        return False
    base = recipe["servings"]
    factor = servings / base if servings and base else 1
    with get_conn() as conn:
        for row in recipe["ingredient_rows"]:
            quantity = None
            if row["quantity"] is not None:
                quantity = round(float(row["quantity"]) * factor, 3)
            conn.execute(UPSERT, (row["name"], row["unit"], quantity, [recipe_id]))
    return True


def list_items():
    with get_conn() as conn:
        items = conn.execute(
            "SELECT id, name, unit, quantity, have, source_recipe_ids "
            "FROM shopping_items ORDER BY lower(name)"
        ).fetchall()
    for item in items:
        item["text"] = item_text(item["quantity"], item["unit"], item["name"])
    return items


def toggle_item(item_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "UPDATE shopping_items SET have = NOT have WHERE id = %s RETURNING id", (item_id,)
        ).fetchone()
    return row is not None


def delete_item(item_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "DELETE FROM shopping_items WHERE id = %s RETURNING id", (item_id,)
        ).fetchone()
    return row is not None


def clear_all():
    with get_conn() as conn:
        conn.execute("DELETE FROM shopping_items")