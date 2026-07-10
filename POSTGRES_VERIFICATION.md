# PostgreSQL Verification

Status: NOT EXECUTED

## Reason

This environment does not currently expose a usable PostgreSQL target:

- `docker --version` failed because Docker is not installed or not available on PATH.
- `POSTGRES_TEST_DATABASE_URL` is not set.

No PostgreSQL result has been fabricated.

## Required Verification Steps

Set a real PostgreSQL test database URL:

```powershell
$env:POSTGRES_TEST_DATABASE_URL="postgresql+asyncpg://user:password@host:5432/contentflow_test"
```

Then run from `apps/api`:

```powershell
$env:DATABASE_URL=$env:POSTGRES_TEST_DATABASE_URL
alembic upgrade head
python -m pytest
```

The PostgreSQL verification must cover:

- Fresh migration install
- Table creation
- Project creation
- Source persistence
- Analysis persistence
- Generated contents persistence
- Full score persistence
- Version history
- Rewrite
- Retry
- Markdown export

## Current Status

SQLite-based tests pass, but they are not a substitute for PostgreSQL runtime verification.
