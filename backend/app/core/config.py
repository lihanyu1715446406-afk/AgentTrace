"""应用配置：基于 pydantic-settings 从环境变量 / .env 读取。"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """AgentTrace 全局配置。

    读取优先级（pydantic-settings 默认）：环境变量 > .env 文件 > 字段默认值。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 服务
    app_name: str = "AgentTrace"
    env: str = "dev"
    log_level: str = "INFO"

    # LLM（DeepSeek，OpenAI 兼容）
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # Embedding（SiliconFlow，OpenAI 兼容；DeepSeek 无 embeddings 接口）
    siliconflow_api_key: str = ""
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"
    siliconflow_embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024

    # Qdrant（M4 RAG + M5 语义记忆）
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "agenttrace_knowledge"
    qdrant_memory_collection: str = "agenttrace_memory"

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "agenttrace"
    postgres_password: str = "agenttrace"
    postgres_db: str = "agenttrace"

    # 诊断任务约束
    max_plan_steps: int = 10
    max_execution_seconds: int = 300
    max_reflection_rounds: int = 3

    @property
    def database_url(self) -> str:
        """SQLAlchemy 异步连接串（asyncpg 驱动）。"""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """返回缓存后的全局配置单例。"""
    return Settings()
