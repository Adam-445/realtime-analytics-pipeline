# Use a minimal Python base image
FROM python:3.13-slim AS base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    netcat-openbsd \
    curl \
    gcc \
    libc-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency list and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt  

FROM base AS production
COPY . .
RUN chmod +x /app/bin/entrypoint.sh
ENTRYPOINT ["/app/bin/entrypoint.sh"]

FROM base AS test
COPY pyproject.toml /app/
RUN pip install --no-cache-dir pytest pytest-asyncio pytest-mock pytest-cov
COPY . /app/