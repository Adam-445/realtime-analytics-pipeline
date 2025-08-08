FROM python:3.12-slim AS base

WORKDIR /app

# Install system deps (if any needed later for confluent-kafka)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl netcat-openbsd ca-certificates gcc librdkafka-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY bin/entrypoint.sh /app/bin/entrypoint.sh
RUN chmod +x /app/bin/entrypoint.sh

ENV PYTHONUNBUFFERED=1
ENV APP_MODULE=src.main:app

EXPOSE 8000

ENTRYPOINT ["/app/bin/entrypoint.sh"]

# # Test stage
# FROM base as test

# # Install test dependencies
# RUN pip install pytest pytest-asyncio pytest-mock pytest-cov fakeredis httpx

# # Copy test files
# COPY tests ./tests

# # Override entrypoint for tests
# ENTRYPOINT []
