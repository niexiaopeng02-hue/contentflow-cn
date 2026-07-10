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

## Implemented But Not Runtime Verified

- OpenAIProvider
- Docker Compose
- PostgreSQL production runtime
- Full browser end-to-end workflow

## Partial

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

Browser E2E is PARTIAL:

- Landing Page: PASS
- Dashboard route loaded but API fetch failed in the live browser run because the baseline CORS defaults did not include the active dev origin.
- Local CORS defaults were expanded, but old dev processes could not be stopped by the sandbox user, so the fixed server could not be reloaded for a full rerun in this session.

## Baseline Notes

- The current baseline is an MVP code baseline, not proof of production readiness.
- Real OpenAI API execution remains not live verified unless `AI_PROVIDER=openai` and a valid `OPENAI_API_KEY` smoke test succeeds.
- PostgreSQL runtime remains not verified until migrations and integration flows pass against a real PostgreSQL database.
- Browser E2E remains not verified until the documented user flow is executed against running API and web servers.
