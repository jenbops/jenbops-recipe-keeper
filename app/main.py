import os

import psycopg
from fastapi import FastAPI

app = FastAPI(title="Recipe Keeper")


@app.get("/health")
def health():
    # Proves the web app itself is running
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    # Proves the app can reach PostgreSQL
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        row = conn.execute("select 1").fetchone()
    return {"db": "ok" if row == (1,) else "error"}