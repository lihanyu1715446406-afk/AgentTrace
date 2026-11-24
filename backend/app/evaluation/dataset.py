"""标准测试集（golden dataset）：用于评估诊断 Agent 的效果。

样本基于 ``scripts/seed_demo_data.py`` 写入的演示数据（tr-demo-001 成功登录链路、
tr-demo-002 失败支付回调、demo-project），评估前先执行一次 seed。
"""

from __future__ import annotations

from ..schemas.evaluation import EvalSample

STANDARD_DATASET: list[EvalSample] = [
    EvalSample(
        sample_id="trace-detail",
        query="查询 trace tr-demo-001 的详细信息",
        expected_task_type="trace_analysis",
        expected_tool_names=["trace_query"],
        expected_facts=["tr-demo-001"],
    ),
    EvalSample(
        sample_id="error-analysis",
        query="分析 trace tr-demo-002 为什么失败",
        expected_task_type="error_analysis",
        expected_tool_names=["span_query"],
        expected_facts=["超时"],
    ),
    EvalSample(
        sample_id="cost-analysis",
        query="统计 trace tr-demo-001 的 token 用量和成本",
        expected_task_type="cost_analysis",
        expected_tool_names=["cost_analysis"],
        expected_facts=["token"],
    ),
    EvalSample(
        sample_id="general-chat",
        query="你好，介绍一下你自己",
        expected_task_type="general",
        expected_tool_names=[],
        expected_facts=[],
    ),
]
