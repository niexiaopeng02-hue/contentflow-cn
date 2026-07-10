"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, Loader2, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { createProject, generateProject } from "@/lib/api";

const progressSteps = [
  "正在清理内容",
  "正在理解内容",
  "正在提取核心观点",
  "正在分析受众",
  "正在生成小红书内容",
  "正在生成抖音脚本",
  "正在生成公众号文章",
  "正在进行质量评估",
  "生成完成",
];

export default function NewProjectPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [category, setCategory] = useState("知识成长");
  const [sourceType, setSourceType] = useState("文章");
  const [contentStyle, setContentStyle] = useState("knowledge_practical");
  const [targetAudience, setTargetAudience] = useState("内容创作者");
  const [audiencePainPoints, setAudiencePainPoints] = useState("不知道如何开始");
  const [knowledgeLevel, setKnowledgeLevel] = useState("beginner");
  const [contentGoal, setContentGoal] = useState("education");
  const [description, setDescription] = useState("");
  const [rawText, setRawText] = useState("");
  const [platforms, setPlatforms] = useState(["xiaohongshu", "douyin", "wechat"]);
  const [loading, setLoading] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);

  function togglePlatform(platform: string) {
    setPlatforms((current) =>
      current.includes(platform) ? current.filter((item) => item !== platform) : [...current, platform],
    );
  }

  async function submit() {
    setLoading(true);
    setError(null);
    setStepIndex(0);
    const timer = window.setInterval(() => {
      setStepIndex((current) => Math.min(current + 1, progressSteps.length - 2));
    }, 650);
    try {
      const project = await createProject({
        name,
        description,
        category,
        source_type: sourceType,
        content_style: contentStyle,
        target_audience: targetAudience,
        audience_pain_points: audiencePainPoints.split("\n").filter(Boolean),
        audience_knowledge_level: knowledgeLevel,
        content_goal: contentGoal,
        target_platforms: platforms,
      });
      await generateProject(project.id, {
        title: name,
        raw_text: rawText,
        target_platforms: platforms,
      });
      setStepIndex(progressSteps.length - 1);
      router.push(`/projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成失败，请重试。");
    } finally {
      window.clearInterval(timer);
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-background px-5 py-6">
      <div className="mx-auto max-w-4xl">
        <Button asChild variant="ghost" className="mb-4">
          <Link href="/dashboard">
            <ArrowLeft className="h-4 w-4" /> 返回
          </Link>
        </Button>
        <Card>
          <CardHeader>
            <CardTitle>新建内容项目</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4">
              <div className="grid gap-4 md:grid-cols-2">
                <label className="grid gap-2 text-sm font-medium">
                  Project Title
                  <input value={name} onChange={(event) => setName(event.target.value)} className="h-11 rounded-md border border-border bg-card px-3 outline-none focus:ring-2 focus:ring-primary" placeholder="例如：30天学习Python经验分享" />
                </label>
                <label className="grid gap-2 text-sm font-medium">
                  Category
                  <input value={category} onChange={(event) => setCategory(event.target.value)} className="h-11 rounded-md border border-border bg-card px-3 outline-none focus:ring-2 focus:ring-primary" />
                </label>
              </div>
              <label className="grid gap-2 text-sm font-medium">
                Source Type
                <input value={sourceType} onChange={(event) => setSourceType(event.target.value)} className="h-11 rounded-md border border-border bg-card px-3 outline-none focus:ring-2 focus:ring-primary" />
              </label>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="grid gap-2 text-sm font-medium">
                  Content Style
                  <select value={contentStyle} onChange={(event) => setContentStyle(event.target.value)} className="h-11 rounded-md border border-border bg-card px-3 outline-none focus:ring-2 focus:ring-primary">
                    <option value="real_experience">真实经验型</option>
                    <option value="knowledge_practical">知识干货型</option>
                    <option value="opinion">观点表达型</option>
                    <option value="storytelling">故事型</option>
                    <option value="conversational">轻松口语型</option>
                    <option value="professional_analysis">专业分析型</option>
                  </select>
                </label>
                <label className="grid gap-2 text-sm font-medium">
                  Knowledge Level
                  <select value={knowledgeLevel} onChange={(event) => setKnowledgeLevel(event.target.value)} className="h-11 rounded-md border border-border bg-card px-3 outline-none focus:ring-2 focus:ring-primary">
                    <option value="beginner">Beginner</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="advanced">Advanced</option>
                  </select>
                </label>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="grid gap-2 text-sm font-medium">
                  Target Audience
                  <input value={targetAudience} onChange={(event) => setTargetAudience(event.target.value)} className="h-11 rounded-md border border-border bg-card px-3 outline-none focus:ring-2 focus:ring-primary" />
                </label>
                <label className="grid gap-2 text-sm font-medium">
                  Content Goal
                  <input value={contentGoal} onChange={(event) => setContentGoal(event.target.value)} className="h-11 rounded-md border border-border bg-card px-3 outline-none focus:ring-2 focus:ring-primary" />
                </label>
              </div>
              <label className="grid gap-2 text-sm font-medium">
                Audience Pain Points
                <textarea value={audiencePainPoints} onChange={(event) => setAudiencePainPoints(event.target.value)} className="min-h-20 rounded-md border border-border bg-card p-3 outline-none focus:ring-2 focus:ring-primary" />
              </label>
              <label className="grid gap-2 text-sm font-medium">
                Description
                <input value={description} onChange={(event) => setDescription(event.target.value)} className="h-11 rounded-md border border-border bg-card px-3 outline-none focus:ring-2 focus:ring-primary" placeholder="可选" />
              </label>
              <div className="grid gap-2 text-sm font-medium">
                Target Platforms
                <div className="flex flex-wrap gap-2">
                  {[
                    ["xiaohongshu", "小红书"],
                    ["douyin", "抖音"],
                    ["wechat", "公众号"],
                  ].map(([value, label]) => (
                    <Button key={value} type="button" variant={platforms.includes(value) ? "default" : "outline"} onClick={() => togglePlatform(value)}>
                      {label}
                    </Button>
                  ))}
                </div>
              </div>
              <label className="grid gap-2 text-sm font-medium">
                Raw Text
                <textarea value={rawText} onChange={(event) => setRawText(event.target.value)} className="min-h-72 rounded-md border border-border bg-card p-3 leading-7 outline-none focus:ring-2 focus:ring-primary" placeholder="粘贴长内容，至少 80 字" />
              </label>
              {loading ? (
                <div className="rounded-md border border-border bg-muted p-3 text-sm">
                  <Loader2 className="mr-2 inline h-4 w-4 animate-spin" />
                  {progressSteps[stepIndex]}
                </div>
              ) : null}
              {error ? <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
              <Button className="w-fit" onClick={submit} disabled={loading || !name || rawText.length < 80 || platforms.length === 0}>
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                开始生成
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
