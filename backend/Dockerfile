FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir -e ".[dev]"

COPY . /app

EXPOSE 10000
CMD ["sh", "-c", "if [ \"${STATEMENT_CONTAINER_MODE:-false}\" = \"true\" ]; then exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-10000}\"; else alembic upgrade head && python -m scripts.seed && exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-10000}\"; fi"]
