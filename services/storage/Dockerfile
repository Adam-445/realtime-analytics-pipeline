# Use a minimal Python base image
FROM python:3.13-slim

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

# Copy the rest of the application code
COPY . .

# Define the entrypoint
RUN chmod +x /app/bin/entrypoint.sh
ENTRYPOINT ["/app/bin/entrypoint.sh"]