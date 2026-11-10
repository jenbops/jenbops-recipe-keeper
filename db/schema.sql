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