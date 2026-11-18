# API image. Build from apps/api:  docker build -t publifin-api .
# Same layout as the repository (/srv/apps/api, /srv/data) so config.py finds data/ without changes.

# --- Build stage: install dependencies with uv into a virtual environment ---
FROM python:3.14.10-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.8 /uv /bin/uv
WORKDIR /srv/apps/api
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# --- Runtime stage: only the virtual environment and the code ---
FROM python:3.14.10-slim
RUN useradd --create-home --uid 1000 app
WORKDIR /srv/apps/api
COPY --from=build /srv/apps/api/.venv .venv
COPY config.py main.py ./
COPY providers providers
COPY agent agent
COPY rag rag
RUN mkdir -p /srv/data && chown app /srv/data
USER app
ENV PATH="/srv/apps/api/.venv/bin:$PATH" PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
