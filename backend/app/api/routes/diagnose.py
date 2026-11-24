"""AI 诊断路由：触发 Multi-Agent 诊断（M8 REST API）。

诊断依赖真实 LLM（DeepSeek）与只读工具；两者均通过 ``dependencies`` 注入，
测试时可 ``app.dependency_overrides`` 替换为假模型与指向隔离库的工具。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool

from ...agents import MultiAgentOrchestrator
from ...schemas import DiagnoseRequest, SupervisorResult
from ..dependencies import get_llm_dependency, get_tools_dependency

router = APIRouter(prefix="/diagnose", tags=["diagnose"])


@router.post("", response_model=SupervisorResult)
async def diagnose(
    body: DiagnoseRequest,
    llm: BaseChatModel = Depends(get_llm_dependency),
    tools: list[BaseTool] = Depends(get_tools_dependency),
) -> SupervisorResult:
    """执行一次 Multi-Agent 综合诊断并返回结构化结果。"""
    orchestrator = MultiAgentOrchestrator(llm, tools)
    return await orchestrator.arun(body.query)
