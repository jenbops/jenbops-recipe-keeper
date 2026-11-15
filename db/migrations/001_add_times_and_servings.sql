-- Adds optional servings and time fields. Safe to run more than once.
ALTER TABLE recipes
  ADD COLUMN IF NOT EXISTS servings     INTEGER CHECK (servings > 0),
  ADD COLUMN IF NOT EXISTS prep_minutes INTEGER CHECK (prep_minutes >= 0),
  ADD COLUMN IF NOT EXISTS cook_minutes INTEGER CHECK (cook_minutes >= 0);