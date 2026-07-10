import asyncio
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.schemas import ProjectContext, RewriteRequest
from app.services.pipeline import run_text_pipeline
from app.services.providers import OpenAIProvider

INPUT = (
    "普通人学习 AI 有三个常见误区。第一，以为必须先学习复杂技术，"
    "所以迟迟不敢开始。第二，以为工具越多越好，结果每天都在换工具。"
    "第三，以为必须做出完整作品才算学会。更好的方式是从一个真实任务开始，"
    "用一个工具完成一个小成果，再复盘输入、输出和下一步改进。"
)


async def main() -> int:
    if os.getenv("AI_PROVIDER") != "openai" or not os.getenv("OPENAI_API_KEY"):
        print("FAIL: set AI_PROVIDER=openai and OPENAI_API_KEY to run real AI smoke test.")
        return 2
    provider = OpenAIProvider()
    context = ProjectContext(
        category="AI科技",
        target_audience="AI beginners",
        audience_pain_points=["不知道如何开始使用 AI"],
        audience_knowledge_level="beginner",
        content_goal="education",
    )
    _, analysis, generated = await run_text_pipeline(INPUT, provider=provider, context=context)
    platforms = {item.platform for item in generated}
    if not analysis.summary or platforms != {"xiaohongshu", "douyin", "wechat"}:
        print("FAIL: missing analysis or platform output")
        return 1
    first = generated[0]
    strategies = await provider.generate_platform_strategy(analysis, context)
    rewritten = await provider.rewrite_content(
        current_content=dict(first.content),
        analysis=analysis,
        strategy=strategies.xiaohongshu,
        previous_feedback=first.score,
        request=RewriteRequest(instruction="降低 AI 感", instruction_type="reduce_ai_tone"),
        context=context,
    )
    if not rewritten:
        print("FAIL: rewrite failed")
        return 1
    print("PASS: real AI smoke test completed")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
