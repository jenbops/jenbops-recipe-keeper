-- One row per ingredient line. Deleting a recipe deletes its rows (ON DELETE CASCADE).
CREATE TABLE IF NOT EXISTS ingredients (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    recipe_id     BIGINT NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    position      INTEGER NOT NULL,
    quantity      NUMERIC(10,3),
    unit          TEXT,
    name          TEXT NOT NULL,
    note          TEXT,
    original_text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ingredients_recipe_idx ON ingredients (recipe_id, position);