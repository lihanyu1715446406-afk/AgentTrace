"""Evaluation（评估）相关的 Pydantic 数据模型：标准测试集 + 自动化评估 + 评估报告。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvalSample(BaseModel):
    """标准测试集（golden dataset）中的一条样本。"""

    sample_id: str = Field(description="样本唯一标识")
    query: str = Field(description="用户提问")
    expected_task_type: str | None = Field(default=None, description="期望的意图分类")
    expected_tool_names: list[str] = Field(
        default_factory=list, description="期望被调用的工具（至少覆盖这些）"
    )
    expected_facts: list[str] = Field(
        default_factory=list, description="答案应包含的关键事实（子串匹配锚点）"
    )
    golden_answer: str | None = Field(default=None, description="黄金答案（供 LLM-as-judge 参考）")


class CaseOutput(BaseModel):
    """一次样本运行产出的标准化输出（供评估指标计算）。"""

    task_type: str | None = Field(default=None, description="实际意图分类")
    tool_names: list[str] = Field(default_factory=list, description="实际调用的工具名")
    answer: str = Field(default="", description="实际回答")


class EvalCaseResult(BaseModel):
    """单条样本的评估结果。"""

    sample_id: str
    actual_task_type: str | None
    actual_tool_names: list[str]
    actual_answer: str
    task_type_match: bool = Field(description="意图分类是否命中")
    tool_match: bool = Field(description="期望工具是否全部被调用")
    facts_covered: int = Field(description="命中的关键事实数")
    facts_total: int = Field(description="关键事实总数")
    passed: bool = Field(description="综合判定是否通过")


class EvalReport(BaseModel):
    """一次评估的整体报告。"""

    dataset_name: str
    evaluation_mode: str = Field(
        description="deterministic（精确匹配）或 llm_judge（LLM-as-judge）"
    )
    total: int
    passed: int
    task_type_accuracy: float = Field(description="意图分类准确率（0~1）")
    tool_coverage: float = Field(description="工具覆盖比例（0~1）")
    fact_coverage: float = Field(description="关键事实覆盖比例（0~1）")
    cases: list[EvalCaseResult] = Field(default_factory=list)
    summary: str = Field(description="人类可读的评估总结")


class EvaluationDataset(BaseModel):
    """标准测试集（Dashboard 评估页，只读展示）。"""

    dataset_name: str
    metrics: dict[str, str] = Field(description="评估指标名 → 说明")
    samples: list[EvalSample] = Field(default_factory=list)
