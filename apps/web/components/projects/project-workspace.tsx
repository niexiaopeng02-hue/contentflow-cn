"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, Download, Loader2, RefreshCw, Save, Wand2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  exportMarkdown,
  getProject,
  getVersions,
  rewriteGeneratedContent,
  updateGeneratedContent,
  type GeneratedContent,
  type ProjectDetail,
} from "@/lib/api";

const platformLabels = { xiaohongshu: "小红书", douyin: "抖音", wechat: "公众号" };
const rewriteOptions = [
  ["优化标题", "stronger_hook"],
  ["降低 AI 感", "reduce_ai_tone"],
  ["更像真人表达", "more_human"],
  ["增加案例", "add_example"],
  ["缩短内容", "more_concise"],
  ["增加冲突", "stronger_hook"],
  ["更加专业", "more_professional"],
  ["更加轻松", "more_conversational"],
] as const;

function stringifyValue(value: string | string[]) {
  return Array.isArray(value) ? value.join("\n") : value;
}

function parseValue(original: string | string[], value: string) {
  return Array.isArray(original) ? value.split("\n").filter(Boolean) : value;
}

export function ProjectWorkspace({ projectId }: { projectId: string }) {
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [active, setActive] = useState("overview");
  const [selected, setSelected] = useState<GeneratedContent | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [versions, setVersions] = useState<GeneratedContent[]>([]);
  const [compare, setCompare] = useState<GeneratedContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load(preferredContentId?: string, preferredPlatform?: string) {
    setLoading(true);
    setError(null);
    try {
      const data = await getProject(projectId);
      setProject(data);
      const preferred =
        data.generated_contents.find(
          (item) =>
            item.id === preferredContentId ||
            item.content_group_id === preferredContentId ||
            item.platform === preferredPlatform,
        ) ??
        data.generated_contents[0] ??
        null;
      setSelected(preferred);
      if (preferred) setActive(preferred.platform);
    } catch (err) {
      setError(err instanceof Error ? err.message : "无法加载项目");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [projectId]);

  useEffect(() => {
    if (!selected) return;
    setDraft(Object.fromEntries(Object.entries(selected.content).map(([key, value]) => [key, stringifyValue(value)])));
    getVersions(selected.id).then((items) => {
      setVersions(items);
      setCompare(items.length > 1 ? items[items.length - 2] : null);
    });
  }, [selected]);

  const activeScore = selected?.score;
  const navItems = useMemo(
    () => [
      ["overview", "Overview"],
      ["source", "Source Content"],
      ["analysis", "Content Analysis"],
      ["xiaohongshu", "小红书"],
      ["douyin", "抖音"],
      ["wechat", "公众号"],
    ],
    [],
  );

  async function saveVersion() {
    if (!selected) return;
    setSaving(true);
    setMessage(null);
    const nextContent = Object.fromEntries(
      Object.entries(selected.content).map(([key, original]) => [key, parseValue(original, draft[key] ?? "")]),
    );
    try {
      const next = await updateGeneratedContent(selected.id, nextContent);
      setSelected(next);
      await load(next.content_group_id ?? next.id, next.platform);
      setMessage("已保存为新版本");
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function rewrite(instruction: string, instructionType: string) {
    if (!selected) return;
    setSaving(true);
    setMessage(null);
    try {
      const next = await rewriteGeneratedContent(selected.id, {
        instruction,
        instruction_type: instructionType,
        target: "full_content",
      });
      setSelected(next);
      await load(next.content_group_id ?? next.id, next.platform);
      setMessage("Rewrite 已生成新版本");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rewrite 失败");
    } finally {
      setSaving(false);
    }
  }

  async function downloadExport() {
    const markdown = await exportMarkdown(projectId);
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${project?.name ?? projectId}.md`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function selectPlatform(platform: string) {
    setActive(platform);
    const content = project?.generated_contents.find((item) => item.platform === platform);
    if (content) setSelected(content);
  }

  return (
    <div className="grid min-h-screen grid-cols-1 bg-background lg:grid-cols-[240px_minmax(0,1fr)_320px]">
      <aside className="border-b border-border bg-card p-4 lg:border-b-0 lg:border-r">
        <Button asChild variant="ghost" className="mb-4">
          <Link href="/dashboard">
            <ArrowLeft className="h-4 w-4" /> Dashboard
          </Link>
        </Button>
        <div className="mb-4 text-lg font-semibold">{project?.name ?? "Project"}</div>
        <nav className="grid gap-2 text-sm">
          {navItems.map(([key, label]) => (
            <button key={key} onClick={() => (["xiaohongshu", "douyin", "wechat"].includes(key) ? selectPlatform(key) : setActive(key))} className={`rounded-md px-3 py-2 text-left ${active === key ? "bg-muted font-medium" : "text-muted-foreground hover:bg-muted"}`}>
              {label}
            </button>
          ))}
        </nav>
      </aside>

      <main className="min-w-0 p-4 md:p-6">
        <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <h1 className="text-2xl font-semibold">{project?.name ?? "Loading"}</h1>
            <p className="mt-1 text-sm text-muted-foreground">{project?.status} · {project?.category} · {project?.source_type}</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => load()}>
              <RefreshCw className="h-4 w-4" /> 刷新
            </Button>
            <Button variant="outline" onClick={downloadExport}>
              <Download className="h-4 w-4" /> Export Markdown
            </Button>
          </div>
        </div>

        {loading ? (
          <div className="flex min-h-96 items-center justify-center text-muted-foreground">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> 正在加载项目
          </div>
        ) : error ? (
          <Card><CardContent className="p-5 text-sm text-red-700">{error}</CardContent></Card>
        ) : project ? (
          <div className="grid gap-5">
            {active === "overview" && (
              <Card>
                <CardHeader><CardTitle>Project Overview</CardTitle></CardHeader>
                <CardContent className="grid gap-4 text-sm leading-7">
                  <p>{project.analysis?.summary}</p>
                  <div><strong>Core Ideas</strong><ul>{project.analysis?.core_ideas.map((item) => <li key={item}>- {item}</li>)}</ul></div>
                  <div><strong>Audience</strong><p>{project.analysis?.target_audience.join(", ")}</p></div>
                  <div><strong>Content Angle</strong><p>{project.analysis?.content_angle}</p></div>
                  <div><strong>Platforms</strong><p>{project.target_platforms.join(", ")}</p></div>
                </CardContent>
              </Card>
            )}

            {active === "source" && (
              <Card>
                <CardHeader><CardTitle>Source Content</CardTitle></CardHeader>
                <CardContent><p className="whitespace-pre-wrap text-sm leading-7">{project.source_content?.raw_text}</p></CardContent>
              </Card>
            )}

            {active === "analysis" && (
              <Card>
                <CardHeader><CardTitle>Content Analysis</CardTitle></CardHeader>
                <CardContent className="grid gap-4 text-sm leading-7">
                  {project.analysis?.topics.map((topic) => (
                    <div key={topic.title} className="rounded-md border border-border p-3">
                      <div className="font-medium">{topic.title}</div>
                      <p className="text-muted-foreground">{topic.description}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            {["xiaohongshu", "douyin", "wechat"].includes(active) && selected && (
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>{platformLabels[selected.platform]} · Version {selected.version}</CardTitle>
                  <Button onClick={saveVersion} disabled={saving}>
                    {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} 保存新版本
                  </Button>
                </CardHeader>
                <CardContent className="grid gap-5">
                  {message ? <div className="rounded-md bg-muted p-3 text-sm">{message}</div> : null}
                  {Object.entries(selected.content).map(([key, value]) => (
                    <label key={key} className="grid gap-2 text-sm font-medium">
                      {key.replaceAll("_", " ")}
                      <textarea value={draft[key] ?? ""} onChange={(event) => setDraft((current) => ({ ...current, [key]: event.target.value }))} className="min-h-28 rounded-md border border-border bg-card p-3 font-normal leading-7 outline-none focus:ring-2 focus:ring-primary" />
                    </label>
                  ))}
                  <div>
                    <div className="mb-2 text-sm font-semibold">Rewrite Engine</div>
                    <div className="flex flex-wrap gap-2">
                      {rewriteOptions.map(([label, type]) => (
                        <Button key={label} size="sm" variant="outline" onClick={() => rewrite(label, type)} disabled={saving}>
                          <Wand2 className="h-4 w-4" /> {label}
                        </Button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <div className="mb-2 text-sm font-semibold">Version History</div>
                    <div className="grid gap-2">
                      {versions.map((version) => (
                        <button key={version.id} onClick={() => setCompare(version)} className="rounded-md border border-border px-3 py-2 text-left text-sm hover:bg-muted">
                          Version {version.version} · {version.source} · Score {version.score.overall_score} · AI Risk {version.score.ai_risk_level} · {new Date(version.created_at).toLocaleString()}
                        </button>
                      ))}
                    </div>
                  </div>
                  {compare ? (
                    <div className="grid gap-3 md:grid-cols-2">
                      <pre className="max-h-96 overflow-auto rounded-md bg-muted p-3 text-xs whitespace-pre-wrap">{JSON.stringify({ score: compare.score, content: compare.content }, null, 2)}</pre>
                      <pre className="max-h-96 overflow-auto rounded-md bg-muted p-3 text-xs whitespace-pre-wrap">{JSON.stringify({ score: selected.score, content: selected.content }, null, 2)}</pre>
                    </div>
                  ) : null}
                </CardContent>
              </Card>
            )}
          </div>
        ) : null}
      </main>

      <aside className="border-t border-border bg-card p-4 lg:border-l lg:border-t-0">
        <h2 className="mb-4 text-base font-semibold">Quality Score</h2>
        {activeScore ? (
          <div className="grid gap-4">
            <div className="rounded-lg border border-border p-4">
              <div className="text-sm text-muted-foreground">Overall</div>
              <div className="mt-1 text-4xl font-semibold">{activeScore.overall_score}</div>
            </div>
            {[
              ["Hook", activeScore.hook_score],
              ["Readability", activeScore.readability_score],
              ["Value", activeScore.value_score],
              ["Structure", activeScore.structure_score],
              ["AI Risk", activeScore.ai_risk_score],
            ].map(([label, score]) => (
              <div key={label} className="grid gap-1">
                <div className="flex justify-between text-sm"><span>{label}</span><span>{score}</span></div>
                <div className="h-2 rounded-sm bg-muted"><div className="h-2 rounded-sm bg-primary" style={{ width: `${score}%` }} /></div>
              </div>
            ))}
            <div>
              <h3 className="mb-2 text-sm font-semibold">Score Breakdown</h3>
              <div className="grid gap-2">
                {Object.entries(activeScore.dimensions ?? {}).map(([key, value]) => (
                  <div key={key} className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{key}</span>
                    <span>{value}</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <h3 className="mb-2 text-sm font-semibold">AI Tone Risk</h3>
              <p className="text-sm capitalize">{activeScore.ai_risk_level}</p>
              <ul className="mt-2 grid gap-2 text-sm leading-6 text-muted-foreground">
                {(activeScore.risk_reasons ?? []).map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
            <div>
              <h3 className="mb-2 text-sm font-semibold">Improvement Suggestions</h3>
              <ul className="grid gap-2 text-sm leading-6 text-muted-foreground">
                {(activeScore.rewrite_suggestions ?? []).map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
            <ul className="grid gap-2 text-sm leading-6 text-muted-foreground">
              {activeScore.feedback.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </div>
        ) : (
          <p className="text-sm leading-6 text-muted-foreground">选择平台内容后显示真实评分。</p>
        )}
      </aside>
    </div>
  );
}
