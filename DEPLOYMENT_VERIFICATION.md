# Deployment Verification

Status: PASS

Verification date: 2026-07-16

## Public URLs

- Frontend: `https://web-puce-kappa-40.vercel.app`
- Backend API: `https://contentflow-cn.onrender.com`
- Health check: `https://contentflow-cn.onrender.com/api/v1/health`
- API docs: `https://contentflow-cn.onrender.com/docs`
- Repository: `https://github.com/niexiaopeng02-hue/contentflow-cn`

## Runtime Configuration

- Frontend host: Vercel
- Backend host: Render
- Database: Neon PostgreSQL
- AI provider: MockProvider
- Frontend API base: `https://contentflow-cn.onrender.com/api/v1`
- CORS verification: request from `https://web-puce-kappa-40.vercel.app` returned HTTP 200 with matching `Access-Control-Allow-Origin`.

No database password, API key, or connection string is stored in this document.

## Public API Smoke Test

- `GET /api/v1/health`: PASS, HTTP 200
- `GET /docs`: PASS, HTTP 200
- `POST /api/v1/projects`: PASS with MVP project payload
- `POST /api/v1/projects/{project_id}/generate`: PASS
- `GET /api/v1/projects/{project_id}`: PASS
- `GET /api/v1/projects/{project_id}/export/markdown`: PASS, HTTP 200
- Generated platform outputs: 3
- Latest public verification project: `5ede3385-69c2-44c2-ac80-7744cfd2e1b0`

Dashboard persistence after public verification:

- Total projects: 5
- Generated contents: 14
- Current month projects: 5
- Latest project status: completed

## Public Browser E2E

Public browser verification passed against the Vercel frontend and Render backend.

Verified flow:

```text
Landing -> Dashboard -> Create Project page -> Project workspace
-> Content Analysis -> Xiaohongshu -> Douyin -> WeChat
-> Version History -> Quality Score -> Export Markdown download
```

Generated screenshots:

- `docs/screenshots/01-landing.png`
- `docs/screenshots/02-dashboard.png`
- `docs/screenshots/03-create-project.png`
- `docs/screenshots/04-analysis.png`
- `docs/screenshots/05-xiaohongshu.png`
- `docs/screenshots/06-douyin.png`
- `docs/screenshots/07-wechat.png`
- `docs/screenshots/08-version-history.png`
- `docs/screenshots/09-score-panel.png`
- `docs/screenshots/10-export-markdown.png`

## Database Verification

Public runtime persistence was verified through the API-backed dashboard and project detail endpoints. The latest public verification project persisted:

- Project row
- Source content
- Content analysis
- 3 generated content rows
- Content scores
- Markdown export content

Direct SQL count verification was not written into this repository because production database credentials must not be stored in committed documentation.

## GitHub Actions

Remote CI is green after the deployment documentation update:

- Workflow: `ContentFlow CN CI`
- Latest verified commit: `f5d4f9a99cbc733fe67817b38d3cdb9a10b8db87`
- Latest verified run: `29469984003`
- Backend Unit, Lint, Eval: PASS
- Frontend Typecheck and Build: PASS
- PostgreSQL Integration: PASS

## Known Issues

- The frontend source currently contains mojibake Chinese UI strings in several files. This was not changed during deployment verification.
- A full optional-metadata project create payload returned HTTP 500 once during public verification. The MVP project create payload, generation flow, dashboard, project detail, and export flow passed. This should be investigated in the next fix-only round.
- Render free instances can cold start.
- OpenAIProvider is implemented but not production verified in this deployment; the public demo uses MockProvider.
