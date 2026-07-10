import asyncio
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.schemas import ProjectContext
from app.services.pipeline import run_text_pipeline


def score_case(case: dict, platforms: set[str], analysis_topics: str, generated: list) -> dict:
    expected = set(case["expected_core_topics"])
    keyword_hits = sum(1 for keyword in expected if keyword in analysis_topics)
    return {
        "schema_validity": bool(generated),
        "platform_differentiation": len({str(item.content)[:120] for item in generated})
        == len(generated),
        "required_fields": all(item.content for item in generated),
        "content_length": all(len(str(item.content)) > 80 for item in generated),
        "ai_risk": all(item.score.ai_risk_level in {"low", "medium"} for item in generated),
        "keyword_preservation": keyword_hits >= 1,
        "platforms_ok": platforms == set(case["platforms"]),
    }


async def main() -> None:
    cases = json.loads(Path("evals/content_cases.json").read_text(encoding="utf-8"))
    passed = 0
    for case in cases:
        context = ProjectContext(
            category=case["category"],
            target_audience=case["target_audience"],
            content_goal=case["content_goal"],
        )
        _, analysis, generated = await run_text_pipeline(
            case["input"], target_platforms=case["platforms"], context=context
        )
        result = score_case(
            case,
            {item.platform for item in generated},
            " ".join(
                [analysis.summary]
                + [topic.title + topic.description for topic in analysis.topics]
                + analysis.core_ideas
            ),
            generated,
        )
        ok = all(result.values())
        passed += int(ok)
        print(json.dumps({"category": case["category"], "ok": ok, **result}, ensure_ascii=False))
    print(f"SUMMARY: {passed}/{len(cases)} cases passed heuristic eval")


if __name__ == "__main__":
    asyncio.run(main())
