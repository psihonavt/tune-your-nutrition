from pydantic import BaseModel


class NEntry(BaseModel):
    item: str
    calories: int
    carbs_g: int
    sugars_g: int
    added_sugars_g: int
    protein_g: int
    fat_g: int
    fiber_g: int
    sodium_mg: int
    used_knowledge_base: bool


class NBreakdown(BaseModel):
    entries: list[NEntry]

    def get_total_as_entry(self, title: str) -> "NEntry":
        total_calories = sum([e.calories for e in self.entries])
        total_carbs = sum([e.carbs_g for e in self.entries])
        total_sugars = sum([e.sugars_g for e in self.entries])
        total_added_sugars = sum([e.added_sugars_g for e in self.entries])
        total_protein = sum([e.protein_g for e in self.entries])
        total_fat = sum([e.fat_g for e in self.entries])
        total_fiber = sum([e.fiber_g for e in self.entries])
        total_sodium = sum([e.sodium_mg for e in self.entries])
        return NEntry(
            item=title,
            calories=total_calories,
            carbs_g=total_carbs,
            sugars_g=total_sugars,
            added_sugars_g=total_added_sugars,
            protein_g=total_protein,
            fat_g=total_fat,
            fiber_g=total_fiber,
            sodium_mg=total_sodium,
            used_knowledge_base=False,
        )
