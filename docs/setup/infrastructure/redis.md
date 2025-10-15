# Redis

In-memory store for the cache service.

- Image: `redis:8.2-alpine`
- Port: 6379

## Usage

The cache service connects using settings in `services/cache/src/core/config.py` and maintains windowed aggregates and TTLs.
