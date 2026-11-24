"""Evaluation（评估）层：标准测试集 + 自动化评估 + LLM-as-judge。"""

from .dataset import STANDARD_DATASET
from .evaluator import Evaluator, build_llm_judge

__all__ = ["Evaluator", "build_llm_judge", "STANDARD_DATASET"]
