from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    category: str = Field(default="general", max_length=80)
    source_type: str = Field(default="article", max_length=80)
    content_style: str = Field(default="knowledge_practical", max_length=80)
    target_audience: str | None = None
    audience_pain_points: list[str] = Field(default_factory=list)
    audience_knowledge_level: str = Field(default="beginner", max_length=80)
    content_goal: str = Field(default="education", max_length=80)
    target_platforms: list[str] = Field(default_factory=lambda: ["xiaohongshu", "douyin", "wechat"])


class ProjectRead(BaseModel):
    id: str
    name: str
    description: str | None
    category: str
    source_type: str
    content_style: str
    target_audience: str | None
    audience_pain_points: list[str]
    audience_knowledge_level: str
    content_goal: str
    target_platforms: list[str]
    status: str
    failure_stage: str | None = None
    error_message: str | None = None
    retryable: bool = False
    created_at: datetime
    generated_content_count: int = 0

    model_config = {"from_attributes": True}


class ProjectGenerateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    raw_text: str = Field(min_length=80)
    target_platforms: list[str] = Field(default_factory=lambda: ["xiaohongshu", "douyin", "wechat"])


class SourceContentCreate(BaseModel):
    project_id: str
    title: str = Field(min_length=1, max_length=200)
    raw_text: str = Field(min_length=80)


class TopicSegment(BaseModel):
    title: str
    description: str
    evidence: list[str]


class ContentAnalysisSchema(BaseModel):
    summary: str
    topics: list[TopicSegment]
    core_ideas: list[str]
    stories: list[str]
    examples: list[str]
    quotable_points: list[str]
    target_audience: list[str]
    content_angle: str
    tone: str = "natural"
    content_value: str = "actionable"
    audience_pains: list[str]
    platform_strategy: dict[str, object]


class ProjectContext(BaseModel):
    category: str = "general"
    source_type: str = "article"
    content_style: str = "knowledge_practical"
    target_audience: str | None = None
    audience_pain_points: list[str] = Field(default_factory=list)
    audience_knowledge_level: str = "beginner"
    content_goal: str = "education"


class PlatformStrategy(BaseModel):
    platform: Literal["xiaohongshu", "douyin", "wechat"]
    audience_intent: str
    content_angle: str
    hook_strategy: str
    tone: str
    structure: list[str]
    length_target: str
    cta_strategy: str
    information_density: Literal["low", "medium", "high"]
    emotion_level: Literal["low", "medium", "high"]
    commercial_tone: Literal["low", "medium", "high"]
    forbidden_behavior: list[str]


class PlatformStrategySet(BaseModel):
    xiaohongshu: PlatformStrategy
    douyin: PlatformStrategy
    wechat: PlatformStrategy


class XiaohongshuOutput(BaseModel):
    titles: list[str]
    content_versions: list[str]
    cover_text: str
    cover_texts: list[str] = Field(default_factory=list)
    hashtags: list[str]
    interaction_question: str
    cta: str


class DouyinOutput(BaseModel):
    hooks: list[str]
    script_30s: str
    script_60s: str
    titles: list[str]
    subtitle_script: list[str]
    cta: str
    comment_question: str


class WechatOutput(BaseModel):
    titles: list[str]
    abstract: str
    full_article: str
    article: str | None = None
    section_headings: list[str]
    summary: str
    cta: str
    moments_sharing_copy: str
    moments_copy: str | None = None


class AIToneRisk(BaseModel):
    level: Literal["low", "medium", "high"]
    risk_reasons: list[str]
    rewrite_suggestions: list[str]
    risk_flags: list[str]


class ContentScoreSchema(BaseModel):
    overall_score: int
    hook_score: int
    readability_score: int
    value_score: int
    structure_score: int
    ai_risk_score: int
    feedback: list[str]
    dimensions: dict[str, int] = Field(default_factory=dict)
    risk_flags: list[str] = Field(default_factory=list)
    score_version: str = "v2"
    ai_risk_level: Literal["low", "medium", "high"] = "medium"
    risk_reasons: list[str] = Field(default_factory=list)
    rewrite_suggestions: list[str] = Field(default_factory=list)


class GeneratedContentRead(BaseModel):
    id: str | None = None
    content_group_id: str | None = None
    platform: str
    content_type: str = "platform_output"
    version: int
    source: str = "generated"
    content: dict | XiaohongshuOutput | DouyinOutput | WechatOutput
    markdown_export: str
    score: ContentScoreSchema
    created_at: datetime | None = None


class PipelineResponse(BaseModel):
    source_content_id: str | None = None
    analysis_id: str | None = None
    analysis: ContentAnalysisSchema
    generated_contents: list[GeneratedContentRead]


class ProjectDetail(ProjectRead):
    source_content: dict | None = None
    analysis: ContentAnalysisSchema | None = None
    generated_contents: list[GeneratedContentRead] = Field(default_factory=list)


class DashboardStats(BaseModel):
    total_projects: int
    generated_contents: int
    current_month_projects: int
    latest_project: ProjectRead | None
    recent_projects: list[ProjectRead]


class GeneratedContentUpdate(BaseModel):
    content: dict
    source: Literal["manual_edit"] = "manual_edit"


class RewriteRequest(BaseModel):
    instruction: str = Field(min_length=1)
    target: Literal["title", "hook", "body", "cta", "full_content", "both"] = "full_content"
    instruction_type: Literal[
        "more_human",
        "more_conversational",
        "more_professional",
        "more_emotional",
        "more_concise",
        "add_example",
        "reduce_ai_tone",
        "stronger_hook",
        "stronger_structure",
        "custom",
    ] = "custom"


class VersionRead(BaseModel):
    id: str
    content_group_id: str
    platform: str
    content_type: str
    version: int
    source: str
    content: dict
    markdown_export: str
    score: ContentScoreSchema
    created_at: datetime


class ErrorResponse(BaseModel):
    detail: str
