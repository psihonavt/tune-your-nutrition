from abc import ABCMeta, abstractmethod

from magentic import prompt, OpenaiChatModel
from magentic.chat_model.anthropic_chat_model import AnthropicChatModel

from nutrition101.domain import NBreakdown

from .prompts import BREAKDOWNS_FROM_MEALS


class ILLMAnalyzer(metaclass=ABCMeta):
    @abstractmethod
    def get_meal_breakdowns(
        self, meal_descriptions: list[str], knowledge_base_section: str | None
    ) -> list[NBreakdown]: ...


class ClaudeNAnalyzer(ILLMAnalyzer):
    _DEFAULT_MODEL = "claude-3-7-sonnet-latest"
    _MAX_TOKENS = 8192

    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL) -> None:
        self._model = AnthropicChatModel(
            model=model, api_key=api_key, max_tokens=self._MAX_TOKENS
        )

    def get_meal_breakdowns(
        self, meal_descriptions: list[str], knowledge_base_section: str | None
    ) -> list[NBreakdown]:
        @prompt(BREAKDOWNS_FROM_MEALS, model=self._model)
        def _get_breakdowns(
            meal_descriptions, knowledge_base_section
        ) -> list[NBreakdown]: ...

        return _get_breakdowns(
            "|||".join(meal_descriptions), knowledge_base_section or ""
        )


class GrokAnalyzer(ILLMAnalyzer):
    _DEFAULT_MODEL = "grok-3"
    _MAX_TOKENS = 8192

    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL) -> None:
        self._model = OpenaiChatModel(
            model=model,
            api_key=api_key,
            max_tokens=self._MAX_TOKENS,
            base_url="https://api.x.ai/v1",
        )

    def get_meal_breakdowns(
        self, meal_descriptions: list[str], knowledge_base_section: str | None
    ) -> list[NBreakdown]:
        @prompt(BREAKDOWNS_FROM_MEALS, model=self._model)
        def _get_breakdowns(
            meal_descriptions, knowledge_base_section
        ) -> list[NBreakdown]: ...

        return _get_breakdowns(
            "|||".join(meal_descriptions), knowledge_base_section or ""
        )
