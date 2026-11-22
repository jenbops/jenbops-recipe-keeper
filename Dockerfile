# --- base: everything the app needs ---
FROM python:3.14-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /code
# create an unprivileged user to run the app
RUN useradd --create-home --uid 1000 appuser
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

# --- test: adds the test tools and tests; never shipped ---
FROM base AS test
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY pytest.ini .
COPY db ./db
COPY tests ./tests
USER appuser
CMD ["pytest", "-q"]

# --- prod: the LAST stage is what "docker build ." produces by default ---
FROM base AS prod
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]