"""项目模型。"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class Project(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # 只存 API Key 的哈希，不存明文（安全要求）。
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
