-- recipes: one row per recipe
CREATE TABLE IF NOT EXISTS recipes (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title       TEXT NOT NULL,
    ingredients TEXT NOT NULL DEFAULT '',
    steps       TEXT NOT NULL DEFAULT '',
    source_url  TEXT,
    notes       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    servings      INTEGER CHECK (servings > 0),
    prep_minutes  INTEGER CHECK (prep_minutes >= 0),
    cook_minutes  INTEGER CHECK (cook_minutes >= 0),
    -- search_vector: PostgreSQL builds a searchable index of words from these columns automatically
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', title || ' ' || ingredients || ' ' || steps)
    ) STORED
);

-- Generalized Inverted Index (GIN): makes keyword search fast
CREATE INDEX IF NOT EXISTS recipes_search_idx ON recipes USING GIN (search_vector);

-- tags: one row per unique tag name
CREATE TABLE IF NOT EXISTS tags (
    id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

-- recipe_tags: the join table linking recipes to tags
CREATE TABLE IF NOT EXISTS recipe_tags (
    recipe_id BIGINT NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    tag_id    BIGINT NOT NULL REFERENCES tags(id)    ON DELETE CASCADE,
    PRIMARY KEY (recipe_id, tag_id)
);

-- One row per ingredient line. Deleting a recipe deletes its rows (ON DELETE CASCADE).
CREATE TABLE IF NOT EXISTS ingredients (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    recipe_id     BIGINT NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    position      INTEGER NOT NULL,
    quantity      NUMERIC(10,3),
    unit          TEXT,
    name          TEXT NOT NULL,
    note          TEXT,
    section       TEXT,
    original_text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ingredients_recipe_idx ON ingredients (recipe_id, position);

-- One row per thing to buy. Quantities from different recipes are added together.
CREATE TABLE IF NOT EXISTS shopping_items (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name              TEXT NOT NULL,
    unit              TEXT,
    quantity          NUMERIC(10,3),
    have              BOOLEAN NOT NULL DEFAULT false,
    source_recipe_ids BIGINT[] NOT NULL DEFAULT '{}',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Same name (ignoring capitals) + same unit = the same item. This also powers the combining.
CREATE UNIQUE INDEX IF NOT EXISTS shopping_items_key
    ON shopping_items (lower(name), coalesce(unit, ''));

    