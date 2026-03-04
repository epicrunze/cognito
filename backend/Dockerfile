FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency file and install
COPY pyproject.toml .
RUN uv sync --no-dev

# Copy source
COPY app/ ./app/

# Create data directory for DuckDB
RUN mkdir -p /app/data

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
