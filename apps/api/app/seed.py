import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import Project
from app.schemas import ProjectCreate, ProjectGenerateRequest
from app.services.projects import create_project, generate_project, get_demo_user

DEMO_PROJECTS = [
    {
        "name": "30天学习Python经验分享",
        "category": "知识成长",
        "source_type": "学习复盘",
        "text": (
            "我用30天系统学习Python，从变量、函数、文件处理到简单的数据分析。"
            "真正有帮助的不是每天学很多，而是每天完成一个小任务，并记录卡住的地方。"
            "第一个阶段我只练基础语法，第二个阶段开始写脚本自动整理表格，第三个阶段做一个小项目。"
            "这段经历让我意识到，学习编程最重要的是即时反馈和可见成果。"
        ),
    },
    {
        "name": "普通人如何开始做自媒体",
        "category": "个人IP",
        "source_type": "方法文章",
        "text": (
            "普通人做自媒体，不需要一开始就追热点或买设备。先选一个自己能持续输出的主题，"
            "用真实经历建立信任，再把每篇内容拆成观点、案例和行动建议。前三个月最重要的是稳定发布，"
            "观察哪些问题被反复评论，然后围绕这些问题建立内容选题库。"
        ),
    },
    {
        "name": "日本自由行避坑指南",
        "category": "旅行",
        "source_type": "旅行笔记",
        "text": (
            "第一次去日本自由行，最容易低估交通规划、餐厅预约和现金准备。"
            "我的建议是把每天行程控制在两个核心区域，提前确认末班车时间，热门餐厅至少提前一周预约。"
            "如果带长辈或孩子，不要把行程排满，保留临时休息和购物时间，体验会好很多。"
        ),
    },
]


async def seed_demo_data() -> None:
    async with AsyncSessionLocal() as session:
        user = await get_demo_user(session)
        existing = await session.execute(select(Project).where(Project.user_id == user.id))
        existing_names = {project.name for project in existing.scalars().all()}
        for item in DEMO_PROJECTS:
            if item["name"] in existing_names:
                continue
            project = await create_project(
                session,
                ProjectCreate(
                    name=item["name"],
                    description="Demo seed project",
                    category=item["category"],
                    source_type=item["source_type"],
                    target_platforms=["xiaohongshu", "douyin", "wechat"],
                ),
            )
            await generate_project(
                session,
                project.id,
                ProjectGenerateRequest(
                    title=item["name"],
                    raw_text=item["text"],
                    target_platforms=["xiaohongshu", "douyin", "wechat"],
                ),
            )


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
