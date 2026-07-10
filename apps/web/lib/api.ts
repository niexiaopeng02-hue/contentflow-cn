export type Score = {
  overall_score: number;
  hook_score: number;
  readability_score: number;
  value_score: number;
  structure_score: number;
  ai_risk_score: number;
  feedback: string[];
  dimensions: Record<string, number>;
  risk_flags: string[];
  score_version: string;
  ai_risk_level: "low" | "medium" | "high";
  risk_reasons: string[];
  rewrite_suggestions: string[];
};

export type GeneratedContent = {
  id: string;
  content_group_id: string;
  platform: "xiaohongshu" | "douyin" | "wechat";
  content_type: string;
  version: number;
  source: "generated" | "manual_edit" | "ai_rewrite";
  content: Record<string, string | string[]>;
  markdown_export: string;
  score: Score;
  created_at: string;
};

export type Analysis = {
  summary: string;
  topics: { title: string; description: string; evidence: string[] }[];
  core_ideas: string[];
  stories: string[];
  examples: string[];
  quotable_points: string[];
  target_audience: string[];
  content_angle: string;
  audience_pains: string[];
  platform_strategy: Record<string, string>;
};

export type Project = {
  id: string;
  name: string;
  description?: string | null;
  category: string;
  source_type: string;
  content_style: string;
  target_audience?: string | null;
  audience_pain_points: string[];
  audience_knowledge_level: string;
  content_goal: string;
  target_platforms: string[];
  status: "draft" | "processing" | "completed" | "failed";
  error_message?: string | null;
  failure_stage?: string | null;
  retryable: boolean;
  created_at: string;
  generated_content_count: number;
};

export type ProjectDetail = Project & {
  source_content?: {
    id: string;
    title: string;
    raw_text: string;
    cleaned_text: string;
    created_at: string;
  } | null;
  analysis?: Analysis | null;
  generated_contents: GeneratedContent[];
};

export type DashboardStats = {
  total_projects: number;
  generated_contents: number;
  current_month_projects: number;
  latest_project: Project | null;
  recent_projects: Project[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(body.detail ?? "Request failed");
  }
  return response.json();
}

export function getDashboard() {
  return request<DashboardStats>("/dashboard", { cache: "no-store" });
}

export function listProjects() {
  return request<Project[]>("/projects", { cache: "no-store" });
}

export function createProject(payload: {
  name: string;
  description?: string;
  category: string;
  source_type: string;
  content_style: string;
  target_audience?: string;
  audience_pain_points: string[];
  audience_knowledge_level: string;
  content_goal: string;
  target_platforms: string[];
}) {
  return request<Project>("/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function generateProject(
  projectId: string,
  payload: { title: string; raw_text: string; target_platforms: string[] },
) {
  return request(`/projects/${projectId}/generate`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getProject(projectId: string) {
  return request<ProjectDetail>(`/projects/${projectId}`, { cache: "no-store" });
}

export function deleteProject(projectId: string) {
  return fetch(`${API_BASE}/projects/${projectId}`, { method: "DELETE" }).then((response) => {
    if (!response.ok) throw new Error("Delete failed");
  });
}

export function updateGeneratedContent(contentId: string, content: Record<string, string | string[]>) {
  return request<GeneratedContent>(`/generated-contents/${contentId}`, {
    method: "PATCH",
    body: JSON.stringify({ content, source: "manual_edit" }),
  });
}

export function rewriteGeneratedContent(
  contentId: string,
  payload: {
    instruction: string;
    instruction_type?: string;
    target: "title" | "hook" | "body" | "cta" | "full_content" | "both";
  },
) {
  return request<GeneratedContent>(`/generated-contents/${contentId}/rewrite`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getVersions(contentId: string) {
  return request<GeneratedContent[]>(`/generated-contents/${contentId}/versions`, { cache: "no-store" });
}

export async function exportMarkdown(projectId: string) {
  const response = await fetch(`${API_BASE}/projects/${projectId}/export/markdown`);
  if (!response.ok) throw new Error("Export failed");
  return response.text();
}
