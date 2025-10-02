# Base stage with common dependencies
FROM python:3.13-slim AS base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    netcat-openbsd \
    curl && \
    rm -rf /var/lib/apt/lists/*

# Set PYTHONPATH to ensure imports work from /app
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PROMETHEUS_MULTIPROC_DIR=/tmp/prom

# Copy dependency list and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt  

# Production stage
FROM base AS production

# Copy application code
COPY src/ /app/src/
COPY bin/ /app/bin/

# Test stage
FROM base AS test

# Install test dependencies
COPY pyproject.toml .
RUN pip install pytest pytest-asyncio pytest-mock pytest-cov httpx

# Copy all code including tests
COPY . .