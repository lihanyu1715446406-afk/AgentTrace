"""M6 Evaluation 测试：标准测试集 + 自动化评估指标（精确匹配与 LLM-as-judge）。"""

from __future__ import annotations

from backend.app.evaluation import STANDARD_DATASET, Evaluator
from backend.app.schemas.evaluation import CaseOutput, EvalSample


def _run_case_with(outputs: dict[str, CaseOutput]):
    async def run_case(sample: EvalSample) -> CaseOutput:
        return outputs[sample.sample_id]

    return run_case


async def test_evaluate_task_type_and_tool_metrics() -> None:
    dataset = [
        EvalSample(
            sample_id="a",
            query="q",
            expected_task_type="trace_analysis",
            expected_tool_names=["trace_query"],
            expected_facts=["tr-001"],
        ),
        EvalSample(
            sample_id="b",
            query="q",
            expected_task_type="error_analysis",
            expected_tool_names=["span_query"],
            expected_facts=["超时"],
        ),
    ]
    outputs = {
        "a": CaseOutput(
            task_type="trace_analysis",
            tool_names=["trace_query"],
            answer="trace tr-001 执行成功",
        ),
        "b": CaseOutput(
            task_type="cost_analysis",
            tool_names=["cost_analysis"],
            answer="成本正常",
        ),
    }
    report = await Evaluator().evaluate(dataset, _run_case_with(outputs))
    assert report.total == 2
    assert report.task_type_accuracy == 0.5
    assert report.tool_coverage == 0.5
    assert report.passed == 1


async def test_evaluate_fact_coverage() -> None:
    dataset = [
        EvalSample(
            sample_id="a",
            query="q",
            expected_task_type="general",
            expected_tool_names=[],
            expected_facts=["hello", "world"],
        )
    ]
    outputs = {
        "a": CaseOutput(task_type="general", tool_names=[], answer="hello there"),
    }
    report = await Evaluator().evaluate(dataset, _run_case_with(outputs))
    assert report.fact_coverage == 0.5
    assert report.passed == 0  # facts 未全覆盖


async def test_evaluate_llm_judge_mode() -> None:
    dataset = [
        EvalSample(
            sample_id="a",
            query="q",
            expected_task_type="general",
            expected_tool_names=[],
            expected_facts=["hello"],
        )
    ]
    outputs = {
        "a": CaseOutput(task_type="general", tool_names=[], answer="你好"),
    }

    async def judge(sample: EvalSample, output: CaseOutput) -> bool:
        return True

    report = await Evaluator(judge=judge).evaluate(dataset, _run_case_with(outputs))
    assert report.evaluation_mode == "llm_judge"
    # LLM-as-judge 语义判定替代 fact 子串匹配，措辞不同也能判通过
    assert report.passed == 1


async def test_standard_dataset_shape() -> None:
    assert len(STANDARD_DATASET) == 4
    assert {s.sample_id for s in STANDARD_DATASET} == {
        "trace-detail",
        "error-analysis",
        "cost-analysis",
        "general-chat",
    }
    assert all(s.query for s in STANDARD_DATASET)
