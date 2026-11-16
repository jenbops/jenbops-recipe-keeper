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