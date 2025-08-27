import pytest

from nutrition101.domain import NBreakdown
from nutrition101.llm import ILLMAnalyzer


@pytest.fixture()
def llm_analyzer() -> ILLMAnalyzer:
    class TestAnalyzer(ILLMAnalyzer):
        def get_meal_breakdowns(
            self, meal_descriptions: list[str], knowledge_base_section: str | None
        ) -> list[NBreakdown]:
            return []

    return TestAnalyzer()
