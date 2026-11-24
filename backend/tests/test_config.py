"""配置模块测试。"""

from backend.app.core.config import get_settings


def test_database_url_format() -> None:
    url = get_settings().database_url
    assert url.startswith("postgresql+asyncpg://")
    assert "@" in url and "/" in url


def test_defaults() -> None:
    s = get_settings()
    assert s.app_name == "AgentTrace"
    assert s.deepseek_model == "deepseek-chat"
    assert s.max_plan_steps == 10
