FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml ./
COPY shared ./shared
COPY api ./api
COPY ingestor ./ingestor
COPY bootstrap ./bootstrap

RUN pip install --upgrade pip && pip install .

ENV PORT=8080
EXPOSE 8080

# Default to the API; Cloud Run Job overrides the command to "python -m ingestor.main".
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
