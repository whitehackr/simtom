# Use Python 3.9 slim image for smaller size
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install Poetry and dependencies
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --only=main --no-dev

# Copy application code
COPY . .

# Expose port (Railway will override this)
EXPOSE 8000

# Run the FastAPI application (Railway provides PORT env var)
CMD uvicorn simtom.api:app --host 0.0.0.0 --port ${PORT:-8000}