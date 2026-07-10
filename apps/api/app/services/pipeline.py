import re

from app.schemas import (
    ContentAnalysisSchema,
    ContentScoreSchema,
    DouyinOutput,
    GeneratedContentRead,
    PipelineResponse,
    PlatformStrategy,
    ProjectContext,
    WechatOutput,
    XiaohongshuOutput,
)
from app.services.providers import AIProvider, get_provider
from app.services.quality import evaluate_content_v2

SUPPORTED_PLATFORMS = {"xiaohongshu", "douyin", "wechat"}


def clean_content(raw_text: str) -> str:
    text = raw_text.replace("\r\n", "\n").replace("\t", " ")
    text = re.sub(r"[ ]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def evaluate_content(
    platform: str,
    content: XiaohongshuOutput | DouyinOutput | WechatOutput | dict,
    strategy: PlatformStrategy | None = None,
) -> ContentScoreSchema:
    return evaluate_content_v2(platform, content, strategy)


def to_markdown(
    platform: str, content: XiaohongshuOutput | DouyinOutput | WechatOutput | dict
) -> str:
    data = content.model_dump() if hasattr(content, "model_dump") else dict(content)
    lines = [f"# {platform.title()} Output", ""]
    for key, value in data.items():
        title = key.replace("_", " ").title()
        lines.append(f"## {title}")
        if isinstance(value, list):
            lines.extend(f"- {item}" for item in value)
        else:
            lines.append(str(value))
        lines.append("")
    return "\n".join(lines).strip()


async def run_text_pipeline(
    raw_text: str,
    provider: AIProvider | None = None,
    target_platforms: list[str] | None = None,
    context: ProjectContext | None = None,
) -> tuple[str, ContentAnalysisSchema, list[GeneratedContentRead]]:
    ai = provider or get_provider()
    project_context = context or ProjectContext()
    platforms = [
        platform
        for platform in (target_platforms or list(SUPPORTED_PLATFORMS))
        if platform in SUPPORTED_PLATFORMS
    ]
    cleaned_text = clean_content(raw_text)
    analysis = await ai.analyze_content(cleaned_text, project_context)
    strategies = await ai.generate_platform_strategy(analysis, project_context)
    analysis.platform_strategy = {
        "xiaohongshu": strategies.xiaohongshu.model_dump(),
        "douyin": strategies.douyin.model_dump(),
        "wechat": strategies.wechat.model_dump(),
    }

    outputs: list[tuple[str, XiaohongshuOutput | DouyinOutput | WechatOutput]] = []
    if "xiaohongshu" in platforms:
        outputs.append(
            (
                "xiaohongshu",
                await ai.generate_xiaohongshu(analysis, strategies.xiaohongshu, project_context),
            )
        )
    if "douyin" in platforms:
        outputs.append(
            ("douyin", await ai.generate_douyin(analysis, strategies.douyin, project_context))
        )
    if "wechat" in platforms:
        outputs.append(
            ("wechat", await ai.generate_wechat(analysis, strategies.wechat, project_context))
        )

    strategy_by_platform: dict[str, PlatformStrategy] = {
        "xiaohongshu": strategies.xiaohongshu,
        "douyin": strategies.douyin,
        "wechat": strategies.wechat,
    }
    generated = [
        GeneratedContentRead(
            platform=platform,
            version=1,
            content=content,
            markdown_export=to_markdown(platform, content),
            score=await ai.evaluate_content(platform, content, strategy_by_platform.get(platform)),
        )
        for platform, content in outputs
    ]
    return cleaned_text, analysis, generated


async def run_preview_pipeline(raw_text: str) -> PipelineResponse:
    _, analysis, generated = await run_text_pipeline(raw_text)
    return PipelineResponse(analysis=analysis, generated_contents=generated)
