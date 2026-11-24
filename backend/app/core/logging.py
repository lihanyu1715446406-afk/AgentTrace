"""日志配置。"""

from __future__ import annotations

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """初始化根日志：统一格式、输出到 stdout。"""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
