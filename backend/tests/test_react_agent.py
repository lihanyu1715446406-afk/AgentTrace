"""单 Agent（ReAct）测试：用假 LLM 驱动真实工具，验证自主选工具与结果提取。"""

from __future__ import annotations

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from backend.app.agents import DiagnoseAgent
from backend.app.tools import ToolRegistry


class FakeToolCallingModel(GenericFakeChatModel):
    """假模型：不真正绑定工具，仅按预设消息序列返回，用于驱动 ReAct 循环。

    ``create_agent`` 会调用 ``bind_tools``，而 ``GenericFakeChatModel`` 未实现该方法
    （会抛 NotImplementedError），故在此覆写为返回自身。
    """

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        return self


async def test_agent_calls_tool_and_extracts_result(seeded, session_factory):
    fake = FakeToolCallingModel(
        messages=iter(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "trace_query",
                            "args": {"trace_id": seeded["trace_id"]},
                            "id": "call-1",
                            "type": "tool_call",
                        }
                    ],
                ),
                AIMessage(content="该 trace 执行成功，状态为 success。"),
            ]
        )
    )
    tools = ToolRegistry(session_factory).build_all()
    agent = DiagnoseAgent(fake, tools)

    result = await agent.arun("查询这条 trace 的详情")

    assert result.answer == "该 trace 执行成功，状态为 success。"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool_name == "trace_query"
    assert seeded["trace_id"] in result.tool_calls[0].output


async def test_agent_answers_without_tools(session_factory):
    fake = FakeToolCallingModel(messages=iter([AIMessage(content="无需工具，直接回答。")]))
    tools = ToolRegistry(session_factory).build_all()
    agent = DiagnoseAgent(fake, tools)

    result = await agent.arun("你好")

    assert result.answer == "无需工具，直接回答。"
    assert result.tool_calls == []
