import pytest

from app.services.pipeline import clean_content, run_preview_pipeline


def test_clean_content_normalizes_spacing() -> None:
    assert clean_content("  hello   world\r\n\r\n\r\nnext ") == "hello world\n\nnext"


@pytest.mark.asyncio
async def test_preview_pipeline_generates_three_platforms() -> None:
    raw = (
        "内容创作者经常把一篇长内容拆成多个平台版本，但如果只是改写原文，"
        "最终会失去观点层次。更好的方式是先分析主题、核心观点、案例和受众，"
        "再针对小红书、抖音和微信公众号分别生成内容。"
    )
    response = await run_preview_pipeline(raw)

    assert response.analysis.summary
    assert len(response.analysis.core_ideas) >= 3
    assert {item.platform for item in response.generated_contents} == {
        "xiaohongshu",
        "douyin",
        "wechat",
    }
    assert all(item.score.overall_score >= 70 for item in response.generated_contents)
    assert response.generated_contents[0].markdown_export.startswith("# Xiaohongshu")
