"""共享 HTTP 客户端工厂：Windows 上用系统证书库覆盖 certifi。"""

from __future__ import annotations

import ssl
import sys

import httpx2


def build_http_clients() -> tuple[httpx2.Client | None, httpx2.AsyncClient | None]:
    """Windows 上为 LLM / Embedding 客户端显式启用系统证书库。

    openai 底层 httpx2 默认走 certifi（Mozilla CA 库），可能缺部分国内 CA。本机实测：
    curl（Windows schannel）能验证 DeepSeek 证书，但 Python（certifi）报「根证书不受
    信任」。``ssl.create_default_context()`` 在 Windows 上会从系统证书存储加载根证书，
    故此处显式覆盖；其余平台维持 httpx2 默认（返回 None）。
    """
    if sys.platform != "win32":
        return None, None
    ctx = ssl.create_default_context()
    return httpx2.Client(verify=ctx), httpx2.AsyncClient(verify=ctx)
