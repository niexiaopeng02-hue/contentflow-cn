from pathlib import Path


def test_initial_migration_contains_required_tables() -> None:
    migration = Path("alembic/versions/20260710_0001_initial.py").read_text(encoding="utf-8")
    for table in [
        "users",
        "projects",
        "source_contents",
        "content_analysis",
        "generated_contents",
        "content_scores",
    ]:
        assert f'"{table}"' in migration
