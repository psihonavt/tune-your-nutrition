from abc import ABCMeta, abstractmethod

from magentic import prompt, OpenaiChatModel
from magentic.chat_model.anthropic_chat_model import AnthropicChatModel

from nutrition101.domain import NBreakdown

_LLM_PROMPT = """Analyze this meal descriptions and break them down into individual food items with their nutritional values. 
Return total sugars in sugars_g field; the field added_sugars_g is only for added/free sugar. added_sugars_g is always <= sugars_g. 
Meal descriptions are separated ONLY by '|||'. For example, `1 1/4 (by volume) cooked pinto beans, 3/4 (by volume) cooked rice, 1 Costco rotisserie chicken thigh, 1 tomatoe.
1/6 zapekanka. 7 dried date, 4 dried figs.` is a SINGLE meal description, despite it having new lines and `.` in its content.

    Meal Descriptions: {meal_descriptions}

    Knowledge base: {knowledge_base_section}

    Instructions:
    - Break down the meal into individual food items/ingredients
    - Use realistic portion sizes based on the description
    - If portion size is not specified, assume standard serving sizes
    - Include all items mentioned (main dishes, sides, beverages, condiments, etc.)
    - For prepared dishes, break down into main components when possible
    - **IMPORTANT: Only use recipes from the Knowledge Base if the meal description explicitly mentions the recipe NAME or clearly describes the complete dish. Do NOT use a recipe just because one ingredient matches.
      If Knowledge Base has more than one recipe with the same name, use the recipe that appears in the text the latest.**
    - **Examples of when to use Knowledge Base recipes:**
      - "Had chicken stew" → Use chicken stew recipe
      - "Made the lasagna recipe" → Use lasagna recipe
      - "Ate leftover beef chili" → Use beef chili recipe if available
    - **Examples of when NOT to use Knowledge Base recipes:**
      - "Had 5 baby carrots" → Just count as individual carrots, don't use chicken stew recipe
      - "Cooked some rice" → Just count as rice, don't use any recipe containing rice
      - "Grilled chicken breast" → Just count as chicken, don't use recipes that contain chicken
    - If a recipe is mentioned by name but not found in the Knowledge Base, make reasonable estimates based on typical versions of that dish
    - Provide nutritional estimates based on USDA standards or common nutritional databases
    - All values should be numbers (no units in the values)
    - If a nutrient value is negligible, use 0"""


class ILLMAnalyzer(metaclass=ABCMeta):
    @abstractmethod
    def get_meals_breakdowns(
        self, meal_descriptions: list[str], knowledge_base_section: str | None
    ) -> list[NBreakdown]: ...


class ClaudeNAnalyzer(ILLMAnalyzer):
    _DEFAULT_MODEL = "claude-3-7-sonnet-latest"
    _MAX_TOKENS = 8192

    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL) -> None:
        self._model = AnthropicChatModel(
            model=model, api_key=api_key, max_tokens=self._MAX_TOKENS
        )

    def get_meals_breakdowns(
        self, meal_descriptions: list[str], knowledge_base_section: str | None
    ) -> list[NBreakdown]:
        @prompt(_LLM_PROMPT, model=self._model)
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

    def get_meals_breakdowns(
        self, meal_descriptions: list[str], knowledge_base_section: str | None
    ) -> list[NBreakdown]:
        @prompt(_LLM_PROMPT, model=self._model)
        def _get_breakdowns(
            meal_descriptions, knowledge_base_section
        ) -> list[NBreakdown]: ...

        return _get_breakdowns(
            "|||".join(meal_descriptions), knowledge_base_section or ""
        )
