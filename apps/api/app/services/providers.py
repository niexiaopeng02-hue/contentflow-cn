import asyncio
import json
from abc import ABC, abstractmethod
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.prompts import (
    ANALYSIS_PROMPT,
    DOUYIN_PROMPT,
    EVALUATOR_PROMPT,
    REWRITE_PROMPT,
    STRATEGY_PROMPT,
    WECHAT_PROMPT,
    XIAOHONGSHU_PROMPT,
)
from app.schemas import (
    ContentAnalysisSchema,
    ContentScoreSchema,
    DouyinOutput,
    PlatformStrategy,
    PlatformStrategySet,
    ProjectContext,
    RewriteRequest,
    WechatOutput,
    XiaohongshuOutput,
)
from app.services.quality import evaluate_content_v2

T = TypeVar("T", bound=BaseModel)


class ProviderError(RuntimeError):
    stage = "provider"
    retryable = True


class ProviderTimeoutError(ProviderError):
    stage = "provider_timeout"


class ProviderRateLimitError(ProviderError):
    stage = "provider_rate_limit"


class ProviderValidationError(ProviderError):
    stage = "provider_validation"


class ProviderUnavailableError(ProviderError):
    stage = "provider_unavailable"


class PipelineError(RuntimeError):
    def __init__(self, message: str, stage: str = "pipeline", retryable: bool = True) -> None:
        super().__init__(message)
        self.stage = stage
        self.retryable = retryable


class AIProvider(ABC):
    @abstractmethod
    async def analyze_content(
        self, cleaned_text: str, context: ProjectContext
    ) -> ContentAnalysisSchema:
        raise NotImplementedError

    @abstractmethod
    async def generate_platform_strategy(
        self, analysis: ContentAnalysisSchema, context: ProjectContext
    ) -> PlatformStrategySet:
        raise NotImplementedError

    @abstractmethod
    async def generate_xiaohongshu(
        self, analysis: ContentAnalysisSchema, strategy: PlatformStrategy, context: ProjectContext
    ) -> XiaohongshuOutput:
        raise NotImplementedError

    @abstractmethod
    async def generate_douyin(
        self, analysis: ContentAnalysisSchema, strategy: PlatformStrategy, context: ProjectContext
    ) -> DouyinOutput:
        raise NotImplementedError

    @abstractmethod
    async def generate_wechat(
        self, analysis: ContentAnalysisSchema, strategy: PlatformStrategy, context: ProjectContext
    ) -> WechatOutput:
        raise NotImplementedError

    async def evaluate_content(
        self,
        platform: str,
        content: XiaohongshuOutput | DouyinOutput | WechatOutput | dict,
        strategy: PlatformStrategy | None = None,
    ) -> ContentScoreSchema:
        return evaluate_content_v2(platform, content, strategy)

    @abstractmethod
    async def rewrite_content(
        self,
        current_content: dict,
        analysis: ContentAnalysisSchema,
        strategy: PlatformStrategy,
        previous_feedback: ContentScoreSchema,
        request: RewriteRequest,
        context: ProjectContext,
    ) -> dict:
        raise NotImplementedError


class MockProvider(AIProvider):
    def _source_keywords(self, cleaned_text: str, context: ProjectContext) -> list[str]:
        keywords: list[str] = []
        rules = [
            ("学习", ["学习计划", "反馈"]),
            ("反馈", ["反馈"]),
            ("同步", ["沟通", "复盘"]),
            ("汇报", ["沟通"]),
            ("AI", ["AI学习"]),
            ("误区", ["误区"]),
            ("健身", ["训练计划", "恢复"]),
            ("恢复", ["恢复"]),
            ("交通", ["交通", "行程"]),
            ("预约", ["行程"]),
            ("整理", ["整理", "效率"]),
            ("低频物品", ["整理"]),
            ("计划", ["决策", "精力"]),
            ("精力", ["精力"]),
            ("阅读", ["阅读", "陪伴"]),
            ("陪", ["陪伴"]),
            ("客户", ["定位", "客户"]),
            ("场景", ["定位"]),
            ("工具", ["工作流", "效率"]),
            ("创作者", ["工作流"]),
            ("提示词", ["提示词", "场景"]),
            ("久坐", ["久坐", "拉伸"]),
            ("拉伸", ["拉伸"]),
            ("亲子", ["亲子", "节奏"]),
            ("节奏", ["节奏"]),
        ]
        for needle, terms in rules:
            if needle in cleaned_text:
                keywords.extend(terms)
        if context.category and context.category not in keywords:
            keywords.append(context.category)
        deduped: list[str] = []
        for keyword in keywords:
            if keyword not in deduped:
                deduped.append(keyword)
        return deduped[:6]

    async def analyze_content(
        self, cleaned_text: str, context: ProjectContext
    ) -> ContentAnalysisSchema:
        lead = cleaned_text[:90].strip()
        audience = context.target_audience or "中文内容创作者"
        pains = context.audience_pain_points or ["不知道如何拆解长内容", "担心生成内容太像模板"]
        source_keywords = self._source_keywords(cleaned_text, context)
        keyword_text = "、".join(source_keywords) if source_keywords else "原文主题"
        return ContentAnalysisSchema(
            summary=(
                f"这份内容围绕「{lead}」展开，可拆解为问题、方法、案例和行动建议。"
                f"关键词：{keyword_text}。"
            ),
            topics=[
                {
                    "title": f"源内容关键词：{keyword_text}",
                    "description": f"需要保留这些主题信号：{keyword_text}。",
                    "evidence": [lead or "原文开头信息"],
                },
                {
                    "title": "核心问题",
                    "description": f"{audience}需要把长内容转化成不同平台能理解的表达。",
                    "evidence": [lead or "原文开头信息"],
                },
                {
                    "title": "方法框架",
                    "description": "先结构化理解，再进入平台化表达。",
                    "evidence": ["原文包含经验、判断、步骤或建议。"],
                },
                {
                    "title": "行动转化",
                    "description": "把观点落到保存、评论、继续阅读或关注。",
                    "evidence": ["适合形成 CTA 和互动问题。"],
                },
            ],
            core_ideas=[
                f"原文最需要保留的主题包括：{keyword_text}。",
                "长内容复用的关键是先提炼可迁移的洞察，而不是直接改写句子。",
                "平台差异来自阅读场景、用户意图、节奏和信息密度。",
            ],
            stories=["可以用创作者从一篇长内容拆出三类平台资产的场景作为主线。"],
            examples=["把经验文章拆成小红书清单、抖音口播和公众号深度文。"],
            quotable_points=[
                "先理解，再表达，内容才不会变成换皮。",
                "平台差异不是字数差异，而是使用场景差异。",
                "同一个洞察，需要翻译给不同平台的用户。",
            ],
            target_audience=[audience],
            content_angle=f"用{context.content_style}方式把长内容变成可发布资产。",
            tone="自然、具体、克制",
            content_value="可执行的方法和判断框架",
            audience_pains=pains,
            platform_strategy={},
        )

    async def generate_platform_strategy(
        self, analysis: ContentAnalysisSchema, context: ProjectContext
    ) -> PlatformStrategySet:
        return PlatformStrategySet(
            xiaohongshu=PlatformStrategy(
                platform="xiaohongshu",
                audience_intent="发现经验、快速判断是否值得收藏",
                content_angle=f"从真实创作者场景切入：{analysis.content_angle}",
                hook_strategy="用痛点和收益明确的标题吸引收藏",
                tone="自然、个人化、短段落",
                structure=["场景", "问题", "经验", "方法", "总结"],
                length_target="500-900 Chinese characters",
                cta_strategy="引导收藏和评论自己的场景",
                information_density="medium",
                emotion_level="medium",
                commercial_tone="low",
                forbidden_behavior=["过度鸡汤", "虚假经历", "机械 emoji 堆砌", "夸张数据"],
            ),
            douyin=PlatformStrategy(
                platform="douyin",
                audience_intent="快速理解，决定是否继续看",
                content_angle="用一个反常识判断制造开场冲突",
                hook_strategy="前三秒直接指出错误做法或反差",
                tone="口语、短句、节奏明确",
                structure=["3秒Hook", "冲突", "信息", "例子", "结论", "CTA"],
                length_target="30s and 60s scripts",
                cta_strategy="引导评论具体问题",
                information_density="medium",
                emotion_level="medium",
                commercial_tone="low",
                forbidden_behavior=["文章体", "复杂长句", "开头背景过长", "空泛口号"],
            ),
            wechat=PlatformStrategy(
                platform="wechat",
                audience_intent="深度阅读，完整理解方法",
                content_angle="建立问题背景，再给出完整方法论",
                hook_strategy="用清晰标题和开头问题承接深读",
                tone="完整、理性、逻辑清晰",
                structure=["问题", "背景", "观点", "案例", "方法", "总结"],
                length_target="1200-2200 Chinese characters",
                cta_strategy="引导关注后续系统方法",
                information_density="high",
                emotion_level="low",
                commercial_tone="low",
                forbidden_behavior=["小红书语气", "口播式短句堆砌", "大量 emoji", "标题党"],
            ),
        )

    async def generate_xiaohongshu(
        self, analysis: ContentAnalysisSchema, strategy: PlatformStrategy, context: ProjectContext
    ) -> XiaohongshuOutput:
        titles = [
            "别再把长文直接丢给 AI 改写了",
            "一篇长内容，怎么拆成 3 个平台素材",
            "内容复用真正有效的流程",
            "写完长文后，我会先做这 4 步",
            "小红书笔记不是文章缩写版",
            "内容创作者的长文拆解清单",
            "多平台分发前先做结构化分析",
            "让 AI 生成内容不模板的办法",
            "从长文到笔记：可收藏流程",
            "新手做内容复用，先避开这个坑",
        ]
        versions = [
            (
                f"如果你也经常写完长内容却不知道怎么分发，可以先停一下。\n\n"
                f"我现在会先看 3 件事：\n1. 这篇内容真正解决的问题是什么\n"
                f"2. 哪些观点能单独成立\n3. 哪些例子能让读者马上理解\n\n"
                f"重点不是改短，而是把「{analysis.core_ideas[0]}」翻译成平台能读懂的形式。"
            ),
            (
                "我的长内容复用清单：\n\n"
                "- 先清理重复表达\n- 拆出 2-3 个主题\n- 提炼可单独传播的观点\n"
                "- 标记故事、例子、金句\n- 再按平台重组\n\n"
                f"小红书更适合：{strategy.tone}，让读者觉得值得收藏。"
            ),
            (
                "以前我以为多平台分发就是改标题、换字数。\n\n"
                "后来发现，真正决定质量的是前面的分析：读者是谁、痛点是什么、"
                "这个平台需要多高的信息密度。\n\n"
                "这样生成出来的内容才像重新表达，而不是换皮。"
            ),
        ]
        return XiaohongshuOutput(
            titles=titles,
            content_versions=versions,
            cover_text="长内容复用流程",
            cover_texts=["长内容复用流程", "先分析再生成", "一文拆三平台"],
            hashtags=["#内容创作", "#小红书运营", "#AI工具", "#个人IP", "#内容复用"],
            interaction_question="你最想把哪类长内容拆成小红书笔记？",
            cta="收藏这套流程，下次写完长内容可以直接照着拆。",
        )

    async def generate_douyin(
        self, analysis: ContentAnalysisSchema, strategy: PlatformStrategy, context: ProjectContext
    ) -> DouyinOutput:
        return DouyinOutput(
            hooks=[
                "别再让 AI 直接改写你的长文。",
                "内容复用没效果，通常错在第一步。",
                "一篇长文，至少能拆出三种表达。",
                "小红书、抖音、公众号，不是字数不同而已。",
                "真正会做内容的人，先分析，再生成。",
            ],
            script_30s=(
                "你有一篇长内容，先别急着改成小红书或抖音。\n"
                "第一步，删掉重复表达。\n第二步，拆出主题和核心观点。\n"
                "第三步，看平台需要什么节奏。\n"
                "小红书要收藏感，抖音要前三秒抓人，公众号要完整逻辑。\n"
                "这样才是内容复用，不是换皮。"
            ),
            script_60s=(
                "很多人做内容复用，第一步就错了。\n"
                "他们直接说：帮我改成小红书、抖音、公众号。\n"
                "结果当然像模板。\n\n"
                "正确做法是先分析：这篇内容解决什么问题？核心观点是什么？"
                "有没有故事和例子？目标读者最关心什么？\n\n"
                "有了这些，再按平台表达。小红书做清单和收藏，抖音做口语节奏和冲突，"
                "公众号做完整论证。\n\n"
                "同一份内容，应该变成三种表达，而不是三份同义改写。"
            ),
            titles=[
                "长内容复用的正确流程",
                "别再让 AI 直接改写了",
                "一篇文章拆三平台内容",
                "内容创作者的效率工作流",
                "AI 生成前先做这一步",
                "小红书抖音公众号怎么一起做",
                "内容复用不是洗稿",
                "个人 IP 必备内容流程",
                "把长文变成短视频脚本",
                "多平台分发的底层方法",
            ],
            subtitle_script=[
                "先分析",
                "再拆观点",
                "按平台重组",
                "小红书收藏",
                "抖音抓人",
                "公众号讲透",
            ],
            cta="关注我，继续拆内容创作者的 AI 工作流。",
            comment_question="你最想把哪种内容拆成短视频？",
        )

    async def generate_wechat(
        self, analysis: ContentAnalysisSchema, strategy: PlatformStrategy, context: ProjectContext
    ) -> WechatOutput:
        headings = [
            "问题：为什么直接改写不够",
            "分析层：先把内容变成资产",
            "平台层：三种表达逻辑",
            "结论：复用不是换皮",
        ]
        article = (
            f"# {headings[0]}\n\n"
            "很多内容创作者以为，内容复用就是把一篇长文改成不同字数。"
            "但真正影响质量的，是平台背后的阅读场景和用户意图。\n\n"
            f"{analysis.core_ideas[0]}\n\n"
            f"# {headings[1]}\n\n"
            "一篇长内容进入生成之前，应该先完成清洗、主题分段、核心观点提炼、"
            "故事案例识别和受众分析。这样，原文才从一段文本变成可调度的内容资产。\n\n"
            f"# {headings[2]}\n\n"
            "小红书强调发现和收藏，所以表达要短段落、清单化、经验感。"
            "抖音强调快速理解，所以要有前三秒钩子、冲突和口语节奏。"
            "公众号强调完整理解，所以需要问题、背景、观点、案例和方法的递进。\n\n"
            f"# {headings[3]}\n\n"
            "好的内容复用不是简单改写，而是把同一个洞察翻译给不同平台的用户。"
        )
        return WechatOutput(
            titles=[
                "内容复用的关键，不是改写，而是重新理解",
                "一篇长内容如何变成三种平台资产",
                "给内容创作者的 AI 工作流：先分析，再生成",
                "从长文到多平台内容：一套可执行流程",
                "为什么你的 AI 改写总像模板？",
            ],
            abstract=analysis.summary,
            full_article=article,
            article=article,
            section_headings=headings,
            summary="先建立结构化分析，再按平台策略生成，能明显降低模板感。",
            cta="如果你正在搭建内容系统，可以从这套分析流程开始。",
            moments_sharing_copy="内容复用不是改字数，而是把同一个洞察翻译给不同平台的用户。",
            moments_copy="内容复用不是改字数，而是把同一个洞察翻译给不同平台的用户。",
        )

    async def rewrite_content(
        self,
        current_content: dict,
        analysis: ContentAnalysisSchema,
        strategy: PlatformStrategy,
        previous_feedback: ContentScoreSchema,
        request: RewriteRequest,
        context: ProjectContext,
    ) -> dict:
        rewritten = dict(current_content)
        note = (
            f"改写方向：{request.instruction}；"
            f"参考反馈：{'；'.join(previous_feedback.feedback[:2])}"
        )
        title_keys = ["titles", "hooks"]
        body_keys = [
            "content_versions",
            "script_30s",
            "script_60s",
            "subtitle_script",
            "full_article",
            "article",
            "abstract",
            "summary",
        ]
        cta_keys = ["cta", "comment_question", "interaction_question"]
        targets = {
            "title": title_keys,
            "hook": ["hooks", "titles"],
            "body": body_keys,
            "cta": cta_keys,
            "full_content": title_keys + body_keys + cta_keys,
            "both": title_keys + body_keys,
        }[request.target]
        for key in targets:
            value = rewritten.get(key)
            if isinstance(value, list):
                rewritten[key] = [f"{item}｜{request.instruction}" for item in value]
            elif isinstance(value, str):
                rewritten[key] = f"{value}\n\n[{note}]"
        return rewritten

    async def analyze(self, cleaned_text: str) -> ContentAnalysisSchema:
        return await self.analyze_content(cleaned_text, ProjectContext())


class OpenAIProvider(AIProvider):
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise ProviderUnavailableError("OPENAI_API_KEY is required when AI_PROVIDER=openai")
        self.settings = settings

    async def _json_call(self, prompt: str, payload: dict, schema: type[T]) -> T:
        body = {
            "model": self.settings.openai_model,
            "input": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema.__name__,
                    "schema": schema.model_json_schema(),
                    "strict": True,
                }
            },
        }
        last_error: Exception | None = None
        for attempt in range(self.settings.provider_max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self.settings.provider_timeout_seconds
                ) as client:
                    response = await client.post(
                        "https://api.openai.com/v1/responses",
                        headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                        json=body,
                    )
                if response.status_code == 429:
                    raise ProviderRateLimitError("OpenAI rate limit")
                if response.status_code >= 500:
                    raise ProviderUnavailableError("OpenAI unavailable")
                response.raise_for_status()
                data = response.json()
                text = data.get("output_text") or self._extract_output_text(data)
                return schema.model_validate_json(text)
            except httpx.TimeoutException:
                last_error = ProviderTimeoutError("OpenAI request timed out")
            except (ValidationError, json.JSONDecodeError) as exc:
                last_error = ProviderValidationError(f"OpenAI JSON validation failed: {exc}")
            except ProviderError as exc:
                last_error = exc
            except httpx.HTTPError as exc:
                last_error = ProviderUnavailableError(f"OpenAI request failed: {exc}")
            if attempt < self.settings.provider_max_retries:
                await asyncio.sleep(0.6 * (attempt + 1))
        if isinstance(last_error, ProviderError):
            raise last_error
        raise ProviderUnavailableError("OpenAI provider failed")

    def _extract_output_text(self, data: dict) -> str:
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"}:
                    return content.get("text", "")
        raise ProviderValidationError("OpenAI response did not include output_text")

    async def analyze_content(
        self, cleaned_text: str, context: ProjectContext
    ) -> ContentAnalysisSchema:
        return await self._json_call(
            ANALYSIS_PROMPT,
            {"cleaned_text": cleaned_text, "context": context.model_dump()},
            ContentAnalysisSchema,
        )

    async def generate_platform_strategy(
        self, analysis: ContentAnalysisSchema, context: ProjectContext
    ) -> PlatformStrategySet:
        return await self._json_call(
            STRATEGY_PROMPT,
            {"analysis": analysis.model_dump(), "context": context.model_dump()},
            PlatformStrategySet,
        )

    async def generate_xiaohongshu(
        self, analysis: ContentAnalysisSchema, strategy: PlatformStrategy, context: ProjectContext
    ) -> XiaohongshuOutput:
        return await self._json_call(
            XIAOHONGSHU_PROMPT,
            {
                "analysis": analysis.model_dump(),
                "strategy": strategy.model_dump(),
                "context": context.model_dump(),
            },
            XiaohongshuOutput,
        )

    async def generate_douyin(
        self, analysis: ContentAnalysisSchema, strategy: PlatformStrategy, context: ProjectContext
    ) -> DouyinOutput:
        return await self._json_call(
            DOUYIN_PROMPT,
            {
                "analysis": analysis.model_dump(),
                "strategy": strategy.model_dump(),
                "context": context.model_dump(),
            },
            DouyinOutput,
        )

    async def generate_wechat(
        self, analysis: ContentAnalysisSchema, strategy: PlatformStrategy, context: ProjectContext
    ) -> WechatOutput:
        return await self._json_call(
            WECHAT_PROMPT,
            {
                "analysis": analysis.model_dump(),
                "strategy": strategy.model_dump(),
                "context": context.model_dump(),
            },
            WechatOutput,
        )

    async def evaluate_content(
        self,
        platform: str,
        content: XiaohongshuOutput | DouyinOutput | WechatOutput | dict,
        strategy: PlatformStrategy | None = None,
    ) -> ContentScoreSchema:
        return await self._json_call(
            EVALUATOR_PROMPT,
            {
                "platform": platform,
                "content": content.model_dump() if hasattr(content, "model_dump") else content,
                "strategy": strategy.model_dump() if strategy else None,
            },
            ContentScoreSchema,
        )

    async def rewrite_content(
        self,
        current_content: dict,
        analysis: ContentAnalysisSchema,
        strategy: PlatformStrategy,
        previous_feedback: ContentScoreSchema,
        request: RewriteRequest,
        context: ProjectContext,
    ) -> dict:
        schema: type[BaseModel]
        if strategy.platform == "xiaohongshu":
            schema = XiaohongshuOutput
        elif strategy.platform == "douyin":
            schema = DouyinOutput
        else:
            schema = WechatOutput
        result = await self._json_call(
            REWRITE_PROMPT,
            {
                "current_content": current_content,
                "analysis": analysis.model_dump(),
                "strategy": strategy.model_dump(),
                "previous_feedback": previous_feedback.model_dump(),
                "request": request.model_dump(),
                "context": context.model_dump(),
            },
            schema,
        )
        return result.model_dump()


def get_provider() -> AIProvider:
    settings = get_settings()
    selected = (settings.ai_provider or settings.llm_provider).lower()
    if selected == "openai":
        return OpenAIProvider()
    return MockProvider()
