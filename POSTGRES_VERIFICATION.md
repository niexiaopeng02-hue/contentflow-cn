# PostgreSQL Verification

Status: VERIFIED

Provider: Neon temporary test database

Project:
- `contentflow-cn-runtime-test`
- Project ID: `winter-bar-02981125`
- Region: `aws-us-east-1`
- PostgreSQL version: 17
- Cleanup: temporary Neon project was deleted after verification.

Secrets:
- The connection string was used only through environment variables.
- No database credentials were written to project files or committed.

## Migration Verification

Fresh migration command:

```powershell
$env:DATABASE_URL=$env:POSTGRES_TEST_DATABASE_URL
python -m alembic upgrade head
```

Result: PASS

Observed migration chain:

```text
Running upgrade  -> 20260710_0001, initial schema
Running upgrade 20260710_0001 -> 20260710_0002, ai quality fields
Running upgrade 20260710_0002 -> 20260710_0003, score risk details
```

Current revision:

```text
20260710_0003
```

Runtime issue found and fixed:

- PostgreSQL rejected `UPDATE projects SET retryable = 0` because `retryable` is boolean.
- Migration `20260710_0002` now uses PostgreSQL-specific boolean and JSONB updates.
- Migration `20260710_0003` now uses PostgreSQL-specific JSONB update for `risk_details`.

## PostgreSQL Integration Test

Command:

```powershell
$env:POSTGRES_TEST_DATABASE_URL="..."
python -m pytest -m postgres -q
```

Result:

```text
1 passed, 41 deselected
```

Covered:

- Project create
- Source persistence
- Analysis persistence
- Generated contents
- Score full persistence
- Version history
- Rewrite
- Retry failed project
- Markdown export
- Delete behavior
- `risk_details` persistence

## Direct Data Verification

Final retained PostgreSQL data snapshot:

```text
sources: 1
analyses: 1
contents: 5
scores: 5
max_version: 3
risk_rows: 5
```

Direct database checks:

```text
revision: 20260710_0003
table_count: 7
risk_details_column: 1
source_duplicate_groups: 0
analysis_duplicate_groups: 0
orphan_scores: 0
```

## Status

PostgreSQL runtime, migration flow, JSONB score details, retry behavior, versioning, and content persistence are verified against a real PostgreSQL database.
