from .db import get_conn

# SQL snippet: collects a recipe's tag names into a list ('{}' = empty list)
TAGS_AGG = (
    "coalesce(array_agg(t.name ORDER BY t.name) "
    "FILTER (WHERE t.name IS NOT NULL), '{}')"
)


def set_tags(conn, recipe_id: int, tags: list[str]):
    # clean tags: trim spaces, lowercase, remove duplicates and blanks
    for name in {t.strip().lower() for t in tags if t.strip()}:
        tag_id = conn.execute(
            "INSERT INTO tags (name) VALUES (%s) "
            "ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id",
            (name,),
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO recipe_tags (recipe_id, tag_id) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING",
            (recipe_id, tag_id),
        )


def create_recipe(d: dict) -> int:
    with get_conn() as conn:  # commits when the block ends successfully
        rid = conn.execute(
            "INSERT INTO recipes (title, ingredients, steps, source_url, notes) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (d["title"], d["ingredients"], d["steps"], d["source_url"], d["notes"]),
        ).fetchone()["id"]
        set_tags(conn, rid, d["tags"])
    return rid


def update_recipe(rid: int, d: dict) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "UPDATE recipes SET title=%s, ingredients=%s, steps=%s, source_url=%s, "
            "notes=%s, updated_at=now() WHERE id=%s RETURNING id",
            (d["title"], d["ingredients"], d["steps"], d["source_url"], d["notes"], rid),
        ).fetchone()
        if row is None:
            return False
        # replace the tag set: remove old links, then add the new ones
        conn.execute("DELETE FROM recipe_tags WHERE recipe_id = %s", (rid,))
        set_tags(conn, rid, d["tags"])
    return True


def delete_recipe(rid: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "DELETE FROM recipes WHERE id = %s RETURNING id", (rid,)
        ).fetchone()
    return row is not None


def list_recipes(q: str | None = None, tags: list[str] | None = None):
    where, params = [], []
    if q:
        where.append("r.search_vector @@ websearch_to_tsquery('english', %s)")
        params.append(q)
    if tags:
        tags = [t.strip().lower() for t in tags]
        # recipe must have ALL requested tags
        where.append(
            "r.id IN (SELECT rt2.recipe_id FROM recipe_tags rt2 "
            "JOIN tags t2 ON t2.id = rt2.tag_id WHERE t2.name = ANY(%s) "
            "GROUP BY rt2.recipe_id HAVING count(*) = %s)"
        )
        params += [tags, len(tags)]
    sql = (
        f"SELECT r.id, r.title, {TAGS_AGG} AS tags "
        "FROM recipes r "
        "LEFT JOIN recipe_tags rt ON rt.recipe_id = r.id "
        "LEFT JOIN tags t ON t.id = rt.tag_id "
        + ("WHERE " + " AND ".join(where) + " " if where else "")
        + "GROUP BY r.id ORDER BY r.created_at DESC"
    )
    with get_conn() as conn:
        return conn.execute(sql, params).fetchall()


def get_recipe(rid: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT r.id, r.title, r.ingredients, r.steps, r.source_url, r.notes, "
            f"{TAGS_AGG} AS tags "
            "FROM recipes r "
            "LEFT JOIN recipe_tags rt ON rt.recipe_id = r.id "
            "LEFT JOIN tags t ON t.id = rt.tag_id "
            "WHERE r.id = %s GROUP BY r.id",
            (rid,),
        ).fetchone()


def list_tags():
    with get_conn() as conn:
        return conn.execute(
            "SELECT t.name, count(rt.recipe_id) AS recipes "
            "FROM tags t LEFT JOIN recipe_tags rt ON rt.tag_id = t.id "
            "GROUP BY t.id ORDER BY t.name"
        ).fetchall()