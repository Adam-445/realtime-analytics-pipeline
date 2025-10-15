# Contributing

Guidelines for contributing code, tests, and documentation to the real-time analytics pipeline.

## Development Workflow

1. Create a feature branch.
2. Add or update unit tests in the relevant service under `services/*/tests/unit`.
3. Ensure end-to-end tests under `tests/e2e` still pass if you modify cross-service behavior.
4. Update documentation under `/docs` when changing behavior or adding features.

## Coding Standards

- Prefer clear, typed Python with Pydantic for settings and schemas.
- Keep service boundaries clean; avoid leaking service-specific logic into `shared` unless broadly applicable.
- Logging: use JSON logging with redaction patterns from settings.

## Tests

Use the orchestrated test runner. See [Testing](../testing/README.md).

## Adding Processing Jobs

Follow [Adding a New Job](../adding_jobs.md). Ensure corresponding ClickHouse tables and storage paths are updated.

## Pull Requests

- Include a concise summary of changes and rationale.
- Link related issues or docs.
- Ensure CI passes and coverage is acceptable.
