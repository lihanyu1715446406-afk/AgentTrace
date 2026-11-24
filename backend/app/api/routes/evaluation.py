"""评估路由（只读）：返回标准测试集与指标说明，供 Dashboard 展示。"""

from __future__ import annotations

from fastapi import APIRouter

from ...evaluation import STANDARD_DATASET
from ...schemas import EvaluationDataset

router = APIRouter(prefix="/evaluation", tags=["evaluation"])

_METRICS = {
    "task_type_accuracy": "意图分类准确率（0~1）",
    "tool_coverage": "期望工具覆盖比例（0~1）",
    "fact_coverage": "关键事实覆盖比例（0~1）",
    "passed": "综合判定通过（意图 + 工具 + 事实全覆盖）",
    "evaluation_mode": "deterministic（精确匹配）或 llm_judge（LLM-as-judge）",
}


@router.get("/dataset", response_model=EvaluationDataset)
async def get_dataset() -> EvaluationDataset:
    """返回标准测试集（golden dataset）与指标定义。"""
    return EvaluationDataset(
        dataset_name="standard",
        metrics=_METRICS,
        samples=STANDARD_DATASET,
    )
