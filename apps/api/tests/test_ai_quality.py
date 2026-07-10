import pytest
from pydantic import ValidationError

from app.schemas import (
    ContentAnalysisSchema,
    DouyinOutput,
    PlatformStrategy,
    ProjectContext,
    RewriteRequest,
    WechatOutput,
    XiaohongshuOutput,
)
from app.services.pipeline import run_text_pipeline
from app.services.providers import MockProvider, ProviderTimeoutError
from app.services.quality import evaluate_ai_tone_risk, evaluate_content_v2

RAW_TEXT = (
    "普通人学习 AI 经常有三个误区：以为必须先学复杂技术，"
    "以为工具越多越好，以为只有做出完整作品才算学习。"
    "更有效的方法是先选择一个真实任务，用一个工具完成一个小成果，"
    "然后复盘输入、输出和下一步改进。"
)


def strategy(platform: str = "xiaohongshu") -> PlatformStrategy:
    return PlatformStrategy(
        platform=platform,
        audience_intent="学习和收藏",
        content_angle="用真实任务学习 AI",
        hook_strategy="指出常见误区",
        tone="自然",
        structure=["问题", "方法", "例子", "总结"],
        length_target="medium",
        cta_strategy="提问",
        information_density="medium",
        emotion_level="medium",
        commercial_tone="low",
        forbidden_behavior=["fake data"],
    )


@pytest.mark.asyncio
async def test_provider_interface_methods_exist() -> None:
    provider = MockProvider()
    for name in [
        "analyze_content",
        "generate_platform_strategy",
        "generate_xiaohongshu",
        "generate_douyin",
        "generate_wechat",
        "evaluate_content",
        "rewrite_content",
    ]:
        assert callable(getattr(provider, name))


@pytest.mark.asyncio
async def test_mock_provider_structured_output() -> None:
    provider = MockProvider()
    analysis = await provider.analyze_content(
        RAW_TEXT, ProjectContext(target_audience="AI beginners")
    )
    assert analysis.summary
    assert analysis.tone
    assert analysis.content_value
    assert analysis.target_audience == ["AI beginners"]


def test_invalid_structured_output_handling() -> None:
    with pytest.raises(ValidationError):
        ContentAnalysisSchema.model_validate({"summary": "missing required fields"})


@pytest.mark.asyncio
async def test_provider_timeout_error_type() -> None:
    error = ProviderTimeoutError("timeout")
    assert error.retryable is True
    assert error.stage == "provider_timeout"


@pytest.mark.asyncio
async def test_platform_strategy_is_differentiated() -> None:
    provider = MockProvider()
    analysis = await provider.analyze_content(RAW_TEXT, ProjectContext())
    strategies = await provider.generate_platform_strategy(analysis, ProjectContext())
    assert strategies.xiaohongshu.structure != strategies.douyin.structure
    assert strategies.wechat.information_density == "high"


@pytest.mark.asyncio
async def test_xiaohongshu_schema() -> None:
    provider = MockProvider()
    analysis = await provider.analyze_content(RAW_TEXT, ProjectContext())
    output = await provider.generate_xiaohongshu(
        analysis, strategy("xiaohongshu"), ProjectContext()
    )
    assert isinstance(output, XiaohongshuOutput)
    assert len(output.titles) == 10
    assert len(output.content_versions) == 3


@pytest.mark.asyncio
async def test_douyin_schema() -> None:
    provider = MockProvider()
    analysis = await provider.analyze_content(RAW_TEXT, ProjectContext())
    output = await provider.generate_douyin(analysis, strategy("douyin"), ProjectContext())
    assert isinstance(output, DouyinOutput)
    assert len(output.hooks) == 5
    assert output.script_30s != output.script_60s


@pytest.mark.asyncio
async def test_wechat_schema() -> None:
    provider = MockProvider()
    analysis = await provider.analyze_content(RAW_TEXT, ProjectContext())
    output = await provider.generate_wechat(analysis, strategy("wechat"), ProjectContext())
    assert isinstance(output, WechatOutput)
    assert len(output.section_headings) >= 4
    assert output.article


def test_ai_risk_evaluator() -> None:
    risk = evaluate_ai_tone_risk("首先，值得注意的是。其次，总的来说。最后，让我们一起点赞收藏。")
    assert risk.level in {"medium", "high"}
    assert risk.risk_reasons


def test_rule_score() -> None:
    score = evaluate_content_v2("xiaohongshu", {"titles": ["标题"], "cta": "收藏"}, strategy())
    assert score.dimensions["title_score"] >= 80


def test_hybrid_score() -> None:
    score = evaluate_content_v2(
        "douyin",
        {"hooks": ["别急"], "comment_question": "你呢？"},
        strategy("douyin"),
    )
    assert score.score_version == "v2"
    assert score.ai_risk_level in {"low", "medium", "high"}


@pytest.mark.asyncio
async def test_rewrite_feedback_usage() -> None:
    provider = MockProvider()
    analysis = await provider.analyze_content(RAW_TEXT, ProjectContext())
    score = evaluate_content_v2("xiaohongshu", {"titles": ["旧标题"]}, strategy())
    rewritten = await provider.rewrite_content(
        current_content={"titles": ["旧标题"], "cta": "旧 CTA"},
        analysis=analysis,
        strategy=strategy(),
        previous_feedback=score,
        request=RewriteRequest(instruction="更像真人表达", target="full_content"),
        context=ProjectContext(),
    )
    assert "更像真人表达" in str(rewritten)


@pytest.mark.asyncio
async def test_pipeline_uses_platform_strategy() -> None:
    _, analysis, generated = await run_text_pipeline(RAW_TEXT, context=ProjectContext())
    assert isinstance(analysis.platform_strategy["xiaohongshu"], dict)
    assert {item.platform for item in generated} == {"xiaohongshu", "douyin", "wechat"}


@pytest.mark.asyncio
async def test_content_style_affects_analysis() -> None:
    _, analysis, _ = await run_text_pipeline(
        RAW_TEXT,
        context=ProjectContext(content_style="storytelling"),
    )
    assert "storytelling" in analysis.content_angle


@pytest.mark.asyncio
async def test_audience_profile_flows_into_analysis() -> None:
    _, analysis, _ = await run_text_pipeline(
        RAW_TEXT,
        context=ProjectContext(
            target_audience="AI beginners",
            audience_pain_points=["不知道从哪里开始"],
        ),
    )
    assert analysis.target_audience == ["AI beginners"]
    assert "不知道从哪里开始" in analysis.audience_pains
