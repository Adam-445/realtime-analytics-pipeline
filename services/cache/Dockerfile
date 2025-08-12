FROM python:3.12-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS production
COPY src/ /app/src/
COPY bin/entrypoint.sh /app/bin/entrypoint.sh

EXPOSE 8080

RUN chmod +x /app/bin/entrypoint.sh
ENTRYPOINT ["/app/bin/entrypoint.sh"]

FROM base AS test
COPY pyproject.toml /app/
RUN pip install --no-cache-dir pytest pytest-asyncio pytest-mock pytest-cov httpx fakeredis
COPY . /app/
