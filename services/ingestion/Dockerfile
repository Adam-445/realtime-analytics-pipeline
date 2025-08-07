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
ENV PYTHONPATH=/app

# Production stage
FROM base AS production

# Copy dependency list and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt  

# Copy application code
COPY src/ /app/src/
COPY bin/ /app/bin/

# Define the entrypoint
RUN chmod +x /app/bin/entrypoint.sh
ENTRYPOINT ["/app/bin/entrypoint.sh"]

# Test stage
FROM base AS test

# Install production dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install test dependencies
COPY pyproject.toml .
RUN pip install pytest pytest-asyncio pytest-mock pytest-cov httpx

# Copy all code including tests
COPY . .

# Default command for testing
CMD ["python", "-m", "pytest", "tests/unit", "-v", "--cov=src", "--cov-report=term-missing"]