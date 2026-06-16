# Custody Control Assurance Lab — API + security console.
# Synthetic, defensive, read-only. No secrets are baked in.
FROM python:3.12-slim

# uv for fast, reproducible installs (uses the committed uv.lock).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    CAL_HOST=0.0.0.0 \
    CAL_PORT=8000

# Install dependencies first (better layer caching), then the source.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 8000
# Serves the FastAPI API + the static security console at /.
CMD ["uv", "run", "--no-dev", "python", "-m", "cal.api.serve"]
