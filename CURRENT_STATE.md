# Current State

Git history begins from the current baseline commit. Earlier local history is not recoverable from this repository.

## Verified

Backend:
- 41 tests passed in the latest audit run.

Ruff:
- Passed in the latest audit run.

Frontend:
- Typecheck passed in the latest audit run.
- Build passed in the latest audit run.

Mock pipeline:
- Verified by direct runtime execution.

Three-platform structured output:
- Verified in MockProvider for Xiaohongshu, Douyin, and WeChat outputs.

Content eval:
- 15/15 heuristic cases passed.

API integration:
- FastAPI route-level project, generation, content update, version history, rewrite, export, and retry tests passed.

Warnings:
- Project-owned pytest warnings were reduced from 402 to 0.

Browser E2E:
- Core browser workflow verified in MockProvider mode.
- Landing, Dashboard, Create Project, Generate, Workspace, Analysis, Xiaohongshu, Douyin, WeChat, Edit, Version, Rewrite, Compare, and Export button passed.
- Direct browser opening of exported Markdown remained blocked by the browser surface; HTTP Markdown content verification passed.

PostgreSQL:
- Real PostgreSQL runtime verified against a temporary Neon test database.
- Alembic migration chain reached `20260710_0003`.
- PostgreSQL integration test passed.
- Direct data verification found no duplicate source or analysis groups and confirmed `risk_details` rows.

CI:
- GitHub Actions workflow added for backend, frontend, and PostgreSQL integration jobs.

## Implemented But Not Runtime Verified

- OpenAIProvider
- Docker Compose
- GitHub Actions remote run results

## Score Persistence

Score V2 persistence was partial in the baseline.

Persisted in the baseline before this round:
- `dimensions`
- `risk_flags`
- `score_version`

Fixed in this round using `risk_details` JSON persistence:
- `ai_risk_level`
- `risk_reasons`
- `rewrite_suggestions`

Verified after this round:
- Score full persistence
- Score reload
- Rewrite version score persistence

## Browser E2E

Browser E2E core flow is PASS:

- Landing Page: PASS
- Dashboard: PASS
- Create Project: PASS
- Generate: PASS
- Workspace: PASS
- Analysis: PASS
- Three platform outputs: PASS
- Edit and Version 2: PASS
- Rewrite and Version 3: PASS
- Compare: PASS
- Export Markdown button: PASS
- Markdown content completeness: PASS
- Direct browser open for the exported Markdown URL: FAIL due browser-surface `ERR_BLOCKED_BY_CLIENT`.

## Baseline Notes

- The current baseline is an MVP code baseline, not proof of production readiness.
- Real OpenAI API execution remains not live verified unless `AI_PROVIDER=openai` and a valid `OPENAI_API_KEY` smoke test succeeds.
- PostgreSQL runtime has been verified against a temporary Neon test database, not a production database.
- Deployment readiness still depends on pushing to GitHub and observing CI results.
