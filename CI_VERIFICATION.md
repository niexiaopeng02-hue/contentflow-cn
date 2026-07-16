# CI Verification

Status: PASS

Repository: `https://github.com/niexiaopeng02-hue/contentflow-cn`

Latest CI-verified commit: `f5d4f9a99cbc733fe67817b38d3cdb9a10b8db87`

Workflow: `ContentFlow CN CI`

Workflow run: `29469984003`

Run URL: `https://github.com/niexiaopeng02-hue/contentflow-cn/actions/runs/29469984003`

## Jobs

- Backend Unit, Lint, Eval: PASS
- Frontend Typecheck and Build: PASS
- PostgreSQL Integration: PASS

## Notes

- The first remote CI run failed in the PostgreSQL migration step because Alembic migration files used the runtime annotation `sa.TypeEngine`, which is not exposed on the SQLAlchemy top-level module in the CI-installed version.
- Commit `c5d53b6c746888a0ac00e038aa860efcf8ff474b` fixed the migration annotations by importing `TypeEngine` from `sqlalchemy.types`.
- No tests were removed, skipped, or weakened.
- No product features, AI pipeline behavior, UI, authentication, payment, upload, OpenAI, or auto-publishing behavior was changed.
- Commit `f5d4f9a99cbc733fe67817b38d3cdb9a10b8db87` added public deployment verification documentation and screenshots. The same three CI jobs passed for that commit.
