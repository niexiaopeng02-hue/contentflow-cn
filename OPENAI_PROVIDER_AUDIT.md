# OpenAI Provider Audit

Status: IMPLEMENTED, NOT LIVE VERIFIED

## Implemented

- Endpoint: `https://api.openai.com/v1/responses`
- Request body includes:
  - `model`
  - system prompt
  - JSON user payload
  - structured output via `text.format.json_schema`
- Response parsing:
  - Uses `output_text` when present.
  - Falls back to scanning `output[].content[]` for text output.
- Structured validation:
  - Uses Pydantic `model_validate_json`.
- Timeout handling:
  - Converts timeout to `ProviderTimeoutError`.
- Retry:
  - Retries up to `provider_max_retries`.
- 429 handling:
  - Converts to `ProviderRateLimitError`.
- 5xx handling:
  - Converts to `ProviderUnavailableError`.
- Invalid schema handling:
  - Converts validation and JSON errors to `ProviderValidationError`.
- Safe error handling:
  - Public project generation failure returns a generic safe error.

## Evaluator Runtime Path

`EVALUATOR_PROMPT` is now connected to `OpenAIProvider.evaluate_content`.

The runtime path is covered by a unit test that monkeypatches the OpenAI JSON call and asserts:

- `EVALUATOR_PROMPT` is passed.
- `ContentScoreSchema` is requested.
- platform/content/strategy payload is passed.

## Not Live Verified

The real OpenAI smoke test was not executed because no `OPENAI_API_KEY` is available in this environment.

Required live verification:

```powershell
$env:AI_PROVIDER="openai"
$env:OPENAI_API_KEY="..."
python scripts/real_ai_smoke.py
```
