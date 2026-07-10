import Link from "next/link";
import { ArrowRight, FileText, Layers3, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-background">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5">
        <div className="text-lg font-semibold">ContentFlow CN</div>
        <Button asChild variant="outline">
          <Link href="/dashboard">进入工作台</Link>
        </Button>
      </header>

      <section className="mx-auto grid max-w-6xl gap-10 px-5 pb-16 pt-12 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
        <div>
          <p className="mb-4 text-sm font-medium text-primary">AI Content Repurposing Workspace</p>
          <h1 className="max-w-3xl text-4xl font-semibold leading-tight tracking-normal md:text-6xl">
            ContentFlow CN
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-muted-foreground">
            面向中国内容创作者的内容再利用工作台。输入一份长内容，先完成结构化分析，再生成适合小红书、抖音和微信公众号的发布素材。
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button asChild>
              <Link href="/dashboard">
                开始创建 <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/projects/new">新建项目</Link>
            </Button>
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card p-4 shadow-sm">
          <div className="grid gap-3">
            {[
              ["Raw Content", "粘贴访谈、文章、播客稿或课程笔记"],
              ["Content Analysis", "提炼主题、核心观点、案例、金句与受众"],
              ["Platform Output", "生成小红书笔记、抖音脚本和公众号文章"],
            ].map(([title, body], index) => (
              <div key={title} className="flex gap-3 rounded-md border border-border p-4">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-accent text-accent-foreground">
                  {index === 0 ? <FileText className="h-4 w-4" /> : index === 1 ? <Layers3 className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
                </div>
                <div>
                  <div className="font-medium">{title}</div>
                  <div className="mt-1 text-sm leading-6 text-muted-foreground">{body}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
