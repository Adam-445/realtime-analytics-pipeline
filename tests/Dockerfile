FROM python:3.13-slim

WORKDIR /tests

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    netcat-openbsd \
    curl \
    gcc \
    libc-dev && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Keep the container running so we can execute tests in it.
CMD ["tail", "-f", "/dev/null"]