"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, FileText, Loader2, Plus, RefreshCw, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { deleteProject, getDashboard, type DashboardStats } from "@/lib/api";

export function DashboardClient() {
  const [data, setData] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setData(await getDashboard());
    } catch (err) {
      setError(err instanceof Error ? err.message : "无法加载 Dashboard");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function remove(projectId: string) {
    if (!window.confirm("确认删除这个项目？此操作会删除关联内容。")) return;
    await deleteProject(projectId);
    await load();
  }

  return (
    <main className="min-h-screen bg-background p-4 md:p-6">
      <div className="mx-auto max-w-6xl">
        <div className="mb-6 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <h1 className="text-2xl font-semibold">ContentFlow Workspace</h1>
            <p className="mt-1 text-sm text-muted-foreground">真实项目、生成内容和版本历史。</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={load}>
              <RefreshCw className="h-4 w-4" /> 刷新
            </Button>
            <Button asChild>
              <Link href="/projects/new">
                <Plus className="h-4 w-4" /> 新建项目
              </Link>
            </Button>
          </div>
        </div>

        {loading ? (
          <div className="flex min-h-80 items-center justify-center text-muted-foreground">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> 正在加载真实数据
          </div>
        ) : error ? (
          <Card>
            <CardContent className="p-5">
              <p className="mb-3 text-sm text-red-700">{error}</p>
              <Button onClick={load}>重试</Button>
            </CardContent>
          </Card>
        ) : data ? (
          <div className="grid gap-5">
            <div className="grid gap-3 md:grid-cols-4">
              {[
                ["Total Projects", data.total_projects],
                ["Generated Contents", data.generated_contents],
                ["This Month", data.current_month_projects],
                ["Latest Project", data.latest_project?.name ?? "-"],
              ].map(([label, value]) => (
                <Card key={label}>
                  <CardContent className="p-4">
                    <div className="text-xs text-muted-foreground">{label}</div>
                    <div className="mt-2 text-xl font-semibold">{value}</div>
                  </CardContent>
                </Card>
              ))}
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Recent Projects</CardTitle>
              </CardHeader>
              <CardContent>
                {data.recent_projects.length === 0 ? (
                  <div className="flex min-h-56 flex-col items-center justify-center rounded-md border border-dashed border-border text-center text-muted-foreground">
                    <FileText className="mb-3 h-8 w-8" />
                    <p className="text-sm">还没有项目，先创建一份长内容。</p>
                  </div>
                ) : (
                  <div className="grid gap-3">
                    {data.recent_projects.map((project) => (
                      <div key={project.id} className="grid gap-3 rounded-lg border border-border p-4 md:grid-cols-[1fr_auto] md:items-center">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <h2 className="font-semibold">{project.name}</h2>
                            <span className="rounded-sm bg-muted px-2 py-1 text-xs">{project.status}</span>
                          </div>
                          <p className="mt-2 text-sm text-muted-foreground">
                            {project.category} · {project.source_type} · {project.target_platforms.join(", ")} · {project.generated_content_count} contents
                          </p>
                        </div>
                        <div className="flex gap-2">
                          <Button asChild variant="outline" size="sm">
                            <Link href={`/projects/${project.id}`}>
                              打开 <ArrowRight className="h-4 w-4" />
                            </Link>
                          </Button>
                          <Button variant="ghost" size="icon" onClick={() => remove(project.id)} title="删除项目">
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        ) : null}
      </div>
    </main>
  );
}
