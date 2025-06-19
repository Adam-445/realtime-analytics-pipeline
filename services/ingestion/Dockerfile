FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends netcat-openbsd curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . ingestion/

# Make the script executable
RUN chmod +x /app/ingestion/scripts/entrypoint.sh

ENTRYPOINT ["/app/ingestion/scripts/entrypoint.sh"]