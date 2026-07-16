# ContentFlow CN

ContentFlow CN is a database-driven MVP workspace for Chinese content creators. A user can create a project, save source content, run the structured AI pipeline, persist generated platform outputs, edit content into new versions, view version history, rewrite content with the mock provider, and export a project as Markdown.

MockProvider is used by default. The project does not implement payment, ASR, auto-publishing, team features, or production authentication.

## Architecture

```text
contentflow-cn/
  apps/
    api/  FastAPI, SQLAlchemy Async, Alembic, Pydantic
    web/  Next.js, TypeScript, Tailwind CSS, shadcn-style primitives
  docker-compose.yml
```

Backend layers:

- API routes with Pydantic request/response contracts
- Repository layer for SQLAlchemy access
- Project service layer for business transactions
- AI provider abstraction with MockProvider and OpenAIProvider placeholder
- Structured content pipeline and scoring
- Prompt architecture in `app/prompts/`
- Provider-specific structured output validation

Frontend pages:

- `/` Landing page
- `/dashboard` real dashboard from API data
- `/projects/new` create project and run generation
- `/projects/[id]` project workspace, editor, score panel, history, rewrite, export

## Database

Tables:

- `users`
- `projects`
- `source_contents`
- `content_analysis`
- `generated_contents`
- `content_scores`

Important fields:

- `projects.status`: `draft`, `processing`, `completed`, `failed`
- `projects.category`, `source_type`, `target_platforms`
- `generated_contents.platform`
- `generated_contents.content_type`
- `generated_contents.version`
- `generated_contents.source`: `generated`, `manual_edit`, `ai_rewrite`
- `generated_contents.content_group_id` for version history
- JSON columns store structured analysis, platform content, feedback, and platform lists

## Migrations

Alembic is configured in `apps/api/alembic.ini`.

```bash
cd apps/api
alembic upgrade head
```

The initial migration creates all MVP tables. Docker API startup also runs `alembic upgrade head` before starting Uvicorn.

## API

Base URL: `http://localhost:8000/api/v1`

- `GET /health`
- `GET /dashboard`
- `POST /projects`
- `GET /projects`
- `GET /projects/{project_id}`
- `DELETE /projects/{project_id}`
- `POST /projects/{project_id}/generate`
- `GET /projects/{project_id}/analysis`
- `GET /projects/{project_id}/contents`
- `GET /generated-contents/{content_id}`
- `PATCH /generated-contents/{content_id}`
- `POST /generated-contents/{content_id}/rewrite`
- `GET /generated-contents/{content_id}/versions`
- `GET /generated-contents/{content_id}/versions/{version}`
- `GET /projects/{project_id}/export/markdown`
- `POST /pipeline/preview`

All product APIs return Pydantic schemas rather than raw ORM objects.

## AI Pipeline

```text
Raw Content
→ Content Cleaning
→ Content Analysis
→ Topic Segmentation
→ Core Idea Extraction
→ Audience Analysis
→ Platform Strategy
→ Platform Generation
→ Quality Evaluation
→ Final Output
```

Generators use `ContentAnalysisSchema` rather than rewriting raw text directly.

## AI Provider Architecture

Provider selection is controlled by environment variables:

```bash
AI_PROVIDER=mock
AI_PROVIDER=openai
OPENAI_API_KEY=...
```

`MockProvider` remains the default for local development and CI. `OpenAIProvider` performs real HTTP requests, applies timeouts, retries transient failures, and validates JSON responses with Pydantic schemas. Real AI quality depends on the selected provider and prompt configuration.

OpenAI status: implemented, not live verified in this repository unless `scripts/real_ai_smoke.py` succeeds with a valid `OPENAI_API_KEY`.

Provider interface methods:

- `analyze_content`
- `generate_platform_strategy`
- `generate_xiaohongshu`
- `generate_douyin`
- `generate_wechat`
- `evaluate_content`
- `rewrite_content`

## Structured Output

Core AI outputs are validated with Pydantic schemas:

- `ContentAnalysisSchema`
- `PlatformStrategySet`
- `XiaohongshuOutput`
- `DouyinOutput`
- `WechatOutput`
- `ContentScoreSchema`

The pipeline does not parse free-form model text by manual string splitting.

## Prompt Architecture

Prompts live in `apps/api/app/prompts/`:

- `analysis.py`
- `strategy.py`
- `xiaohongshu.py`
- `douyin.py`
- `wechat.py`
- `evaluator.py`
- `rewrite.py`

Each prompt includes role, platform context, objective, input assumptions, output schema, quality constraints, and forbidden behavior.

## Platform Strategy

Before platform generation, the pipeline creates a structured strategy for each platform:

- audience intent
- content angle
- hook strategy
- tone
- structure
- length target
- CTA strategy
- information density
- emotion level
- commercial tone
- forbidden behavior

The three platform generators consume these strategy objects, so outputs differ in structure, language, rhythm, and user intent.

## AI Tone Risk

The AI tone evaluator checks for:

- repeated AI transition phrases
- over-summary
- template CTA
- possible fake data
- possible fake personal experience

It returns `low`, `medium`, or `high`, plus risk reasons and rewrite suggestions.

## Content Score V2

Content Score V2 combines rule-based checks with provider-compatible evaluation hooks. It stores:

- `overall_score`
- `dimensions`
- `feedback`
- `risk_flags`
- `score_version`
- AI risk level, reasons, and rewrite suggestions

Content Score is an internal heuristic and AI-assisted quality signal, not a guarantee of engagement, traffic, or commercial performance.

Score V2 persistence is verified for `dimensions`, `risk_flags`, `score_version`, `ai_risk_level`, `risk_reasons`, and `rewrite_suggestions`. Risk detail fields are persisted in `content_scores.risk_details`.

Platform output coverage:

- 小红书: 10 titles, 3 content versions, cover text, hashtags, interaction question, CTA
- 抖音: 5 hooks, 30-second script, 60-second script, 10 titles, subtitle script, CTA, comment question
- 公众号: 5 titles, abstract, full article, section headings, summary, CTA, Moments sharing copy

## Project Lifecycle

The MVP supports this loop:

```text
Create Project
→ Save Project
→ Save Source Content
→ Run Pipeline
→ Save Analysis
→ Save Generated Contents
→ Save Scores
→ Dashboard Load Real Data
→ Edit Content
→ Save New Version
→ Version History
→ Compare Versions
→ Rewrite
→ Export Markdown
```

Generation uses a transaction-oriented service. If pipeline execution fails, the project is marked `failed`; it is not left as `completed`.

## Versioning

Initial generated content is saved as `version = 1` and `source = generated`.

Manual edits and rewrite operations create a new row:

- `version = previous version + 1`
- old versions remain intact
- scores are recalculated
- `content_group_id` links the history

The first compare view is side-by-side JSON content, without a complex diff library.

## Rewrite Engine V2

Rewrite now accepts:

- target: `title`, `hook`, `body`, `cta`, `full_content`, `both`
- instruction type: `more_human`, `more_conversational`, `more_professional`, `more_emotional`, `more_concise`, `add_example`, `reduce_ai_tone`, `stronger_hook`, `stronger_structure`, `custom`

Rewrite input includes current content, content analysis, platform strategy, previous evaluator feedback, user instruction, and project context.

## Failure Recovery

Provider and pipeline errors are represented as safe errors:

- `ProviderTimeoutError`
- `ProviderRateLimitError`
- `ProviderValidationError`
- `ProviderUnavailableError`
- `PipelineError`

Projects can store `failure_stage`, `error_message`, and `retryable`. Retry endpoint:

```text
POST /api/v1/projects/{project_id}/retry
```

Only retryable failed projects can be retried.

## Local Development

Install backend dependencies:

```bash
cd apps/api
pip install -r requirements.txt
```

Run API:

```bash
cd apps/api
alembic upgrade head
uvicorn app.main:app --reload
```

Install frontend dependencies:

```bash
cd apps/web
npm install
```

Run web:

```bash
cd apps/web
npm run dev
```

Docker:

```bash
docker compose up --build
```

Seed repeatable demo data:

```bash
cd apps/api
python -m app.seed
```

## Testing

Backend:

```bash
cd apps/api
python -m ruff check .
python -m pytest
```

Frontend:

```bash
cd apps/web
npm run typecheck
npm run build
```

Manual real AI smoke test:

```bash
cd apps/api
AI_PROVIDER=openai OPENAI_API_KEY=... python scripts/real_ai_smoke.py
```

This is not required for CI and should only be run manually when a real API key is available.

Content evaluation:

```bash
cd apps/api
python evals/run_content_eval.py
```

The eval set contains 15 Chinese content cases and checks schema validity, platform differentiation, required fields, content length, AI risk, keyword preservation, and requested platforms. The current MockProvider heuristic eval passes 15/15 cases. It does not claim to predict real traffic.

## Verified Locally

- Backend tests: 41 passed
- Backend lint: Ruff passed
- Frontend typecheck: passed
- Frontend build: passed
- Heuristic eval: 15/15 passed
- Browser E2E: core workflow verified in MockProvider mode
- PostgreSQL: migration and integration flow verified against a real Neon PostgreSQL test database

## Browser E2E

The core browser workflow was verified locally with the in-app browser:

```text
Landing -> Dashboard -> Create Project -> Generate -> Workspace -> Analysis
-> Xiaohongshu/Douyin/WeChat outputs -> Edit -> Version 2
-> reduce_ai_tone Rewrite -> Version 3 -> Compare -> Export Markdown
```

Known browser verification gap:

- Direct browser navigation to the local API Markdown export URL was blocked by the browser surface with `ERR_BLOCKED_BY_CLIENT`.
- The Export Markdown button was clicked successfully.
- The Markdown endpoint returned HTTP 200 and contained all three platform sections.

## PostgreSQL Verification

PostgreSQL runtime verification was completed against a temporary Neon test database.

Verified:

- Fresh Alembic migration to `20260710_0003`
- Migration chain `0001 -> 0002 -> 0003`
- PostgreSQL boolean/JSONB migration compatibility
- Project/source/analysis/generated content/score persistence
- Score V2 `risk_details` persistence
- Version history up to Version 3
- Rewrite
- Retry without duplicate source/analysis rows
- Markdown export
- Delete behavior

## GitHub Actions

CI is defined in `.github/workflows/ci.yml` with separate jobs:

- Backend Unit, Lint, Eval
- Frontend Typecheck and Build
- PostgreSQL Integration with a PostgreSQL 17 service

PostgreSQL integration tests are marked with `pytest.mark.postgres` and run only in the PostgreSQL job or when `POSTGRES_TEST_DATABASE_URL` is configured.

Remote CI verification:

- Repository: `https://github.com/niexiaopeng02-hue/contentflow-cn`
- Verified commit: `f5d4f9a99cbc733fe67817b38d3cdb9a10b8db87`
- Workflow run: `29469984003`
- Workflow status: passed
- Backend Unit, Lint, Eval: passed
- Frontend Typecheck and Build: passed
- PostgreSQL Integration: passed

## Live Demo

Public deployment is verified in MockProvider mode:

- Frontend: `https://web-puce-kappa-40.vercel.app`
- Backend API: `https://contentflow-cn.onrender.com`
- Health check: `https://contentflow-cn.onrender.com/api/v1/health`
- API docs: `https://contentflow-cn.onrender.com/docs`
- Deployment verification: `DEPLOYMENT_VERIFICATION.md`
- Screenshots: `docs/screenshots/`

Public verification passed:

- Health check
- API docs
- CORS from Vercel frontend origin
- MVP project creation
- Text generation pipeline
- Three generated platform outputs
- Project detail loading
- Markdown export
- Browser rendering for landing, dashboard, create page, analysis, platform outputs, version history, score panel, and export download

## Current Limitations

- MockProvider is the default AI path.
- OpenAIProvider exists and can make real requests, but was not smoke-tested in this run because no API key was available.
- No real authentication yet; the backend uses a demo user.
- No payment.
- No ASR.
- No video or audio upload.
- No auto-publishing.
- No Redis or Celery.
- No complex team permissions.
- Version compare is side-by-side, not semantic diff.
- Docker configuration exists, but Docker was not runtime verified locally in this environment.
- Public deployment is verified on Vercel + Render in MockProvider mode.
- Several Chinese UI strings are currently mojibake in source and deployed UI; this should be fixed in a dedicated UI text cleanup round.
- A full optional-metadata project create payload returned HTTP 500 once during public deployment verification, while the MVP project create/generate/export flow passed.

## Next Phase

- Wire a production-verified OpenAI provider with strict JSON schemas.
- Add real authentication.
- Improve editor ergonomics and field-specific platform editors.
- Add semantic version diff.
- Add retry/resume behavior for failed projects.
- Add optional background jobs only when generation latency requires it.
