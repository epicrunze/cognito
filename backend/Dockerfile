# Multi-stage Dockerfile for Cognito FastAPI Backend

# Stage 1: Base image with uv
FROM python:3.11-slim as base

# Install uv package manager
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Stage 2: Dependencies installation
FROM base as dependencies

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Stage 3: Production image
FROM python:3.11-slim as production

# Install uv for running the application
RUN pip install --no-cache-dir uv

# Create non-root user for security
RUN useradd -m -u 1000 cognito && \
    mkdir -p /app/data && \
    chown -R cognito:cognito /app

# Set working directory
WORKDIR /app

# Copy installed dependencies from dependencies stage
COPY --from=dependencies --chown=cognito:cognito /app/.venv /app/.venv

# Copy application code
COPY --chown=cognito:cognito app/ /app/app/
COPY --chown=cognito:cognito main.py /app/
COPY --chown=cognito:cognito pyproject.toml /app/

# Switch to non-root user
USER cognito

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
