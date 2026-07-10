import json
import re

from app.schemas import AIToneRisk, ContentScoreSchema, PlatformStrategy

AI_PHRASES = [
    "首先",
    "其次",
    "最后",
    "值得注意的是",
    "总的来说",
    "在这个时代",
    "不难发现",
    "让我们一起",
]

TEMPLATE_CTAS = ["关注我", "点赞收藏", "赶紧收藏", "不要错过"]
FAKE_DATA_PATTERN = re.compile(r"\d+\s*(万|亿|%|倍)")


def _dump(content: object) -> str:
    if hasattr(content, "model_dump_json"):
        return content.model_dump_json(ensure_ascii=False)
    return json.dumps(content, ensure_ascii=False)


def evaluate_ai_tone_risk(content: object) -> AIToneRisk:
    text = _dump(content)
    flags: list[str] = []
    reasons: list[str] = []
    suggestions: list[str] = []

    repeated_phrases = [phrase for phrase in AI_PHRASES if text.count(phrase) >= 2]
    if repeated_phrases:
        flags.append("repeated_ai_transitions")
        reasons.append(f"重复使用 AI 常见连接词：{', '.join(repeated_phrases)}")
        suggestions.append("减少模板化连接词，改用具体场景或动作承接。")

    if text.count("。") > 20 and "我" not in text and "你" not in text:
        flags.append("over_summary")
        reasons.append("文本偏总结陈述，缺少读者或创作者视角。")
        suggestions.append("增加具体对象、场景和可执行动作。")

    if any(cta in text for cta in TEMPLATE_CTAS):
        flags.append("template_cta")
        reasons.append("CTA 有模板化表达。")
        suggestions.append("把 CTA 改成和内容任务相关的问题或行动。")

    if FAKE_DATA_PATTERN.search(text):
        flags.append("possible_fake_data")
        reasons.append("出现数字化效果表达，需要确认来源。")
        suggestions.append("没有来源的数据应删除或改成经验性表述。")

    if "作为一个" in text or "亲测" in text:
        flags.append("possible_fake_personal_experience")
        reasons.append("可能出现未经来源支持的个人经历表达。")
        suggestions.append("只保留原文明确提供的经历，避免虚构第一人称。")

    if len(flags) >= 3:
        level = "high"
    elif flags:
        level = "medium"
    else:
        level = "low"
        reasons.append("未发现明显模板化风险。")
        suggestions.append("发布前补充账号自身真实细节。")

    return AIToneRisk(
        level=level,
        risk_reasons=reasons,
        rewrite_suggestions=suggestions,
        risk_flags=flags,
    )


def _score_by_platform(
    platform: str, text: str, strategy: PlatformStrategy | None
) -> dict[str, int]:
    length = len(text)
    if platform == "xiaohongshu":
        return {
            "title_score": 86 if "titles" in text else 70,
            "hook_score": 82,
            "readability_score": 88 if length < 2500 else 74,
            "information_value_score": 86 if "步骤" in text or "方法" in text else 78,
            "save_value_score": 88 if "清单" in text or "收藏" in text else 76,
            "platform_fit_score": 88 if strategy and strategy.platform == "xiaohongshu" else 78,
            "commercial_pressure_score": 92 if "购买" not in text else 62,
        }
    if platform == "douyin":
        return {
            "hook_score": 88 if "hooks" in text else 72,
            "spoken_language_score": 86 if "\n" in text else 76,
            "rhythm_score": 84 if length < 1800 else 70,
            "retention_potential_score": 82,
            "clarity_score": 86,
            "cta_score": 82 if "comment_question" in text else 70,
        }
    return {
        "title_score": 84 if "titles" in text else 70,
        "structure_score": 90 if "section_headings" in text else 74,
        "logic_score": 86,
        "depth_score": 88 if length > 900 else 72,
        "readability_score": 82,
        "completion_score": 86 if "summary" in text and "cta" in text else 70,
    }


def evaluate_content_v2(
    platform: str,
    content: object,
    strategy: PlatformStrategy | None = None,
) -> ContentScoreSchema:
    text = _dump(content)
    risk = evaluate_ai_tone_risk(content)
    dimensions = _score_by_platform(platform, text, strategy)
    ai_risk_score = {"low": 14, "medium": 38, "high": 68}[risk.level]
    dimensions["ai_risk_signal_score"] = max(30, 100 - ai_risk_score)
    overall = round(sum(dimensions.values()) / len(dimensions))
    feedback = [
        f"平台适配：{platform} 的结构完整度可用。",
        "评分是内部启发式质量信号，不代表真实流量表现。",
        *risk.rewrite_suggestions[:2],
    ]
    return ContentScoreSchema(
        overall_score=overall,
        hook_score=dimensions.get("hook_score", dimensions.get("title_score", 80)),
        readability_score=dimensions.get("readability_score", dimensions.get("clarity_score", 80)),
        value_score=dimensions.get("information_value_score", dimensions.get("depth_score", 82)),
        structure_score=dimensions.get("structure_score", dimensions.get("platform_fit_score", 82)),
        ai_risk_score=ai_risk_score,
        feedback=feedback,
        dimensions=dimensions,
        risk_flags=risk.risk_flags,
        score_version="v2",
        ai_risk_level=risk.level,
        risk_reasons=risk.risk_reasons,
        rewrite_suggestions=risk.rewrite_suggestions,
    )
