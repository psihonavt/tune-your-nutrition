BREAKDOWNS_FROM_MEALS = """Analyze this meal descriptions and break them down into individual food items with their nutritional values. 
Return total sugars in sugars_g field; the field added_sugars_g is only for added/free sugar. added_sugars_g is always <= sugars_g. 
Meal descriptions are separated ONLY by '|||'. For example, `1 1/4 (by volume) cooked pinto beans, 3/4 (by volume) cooked rice, 1 Costco rotisserie chicken thigh, 1 tomatoe.
1/6 zapekanka. 7 dried date, 4 dried figs.` is a SINGLE meal description, despite it having new lines and `.` in its content.

    Meal Descriptions: {meal_descriptions}

    Knowledge base: {knowledge_base_section}

    Return Format:
    You must return a list of NBreakdown objects. Each NBreakdown contains a list of NEntry objects with this exact schema:
    
    NEntry:
    - item: str (name of the food item)
    - calories: int (no units)
    - carbs_g: int (no units)
    - sugars_g: int (total sugars, no units)
    - added_sugars_g: int (added/free sugars only, must be <= sugars_g, no units)
    - protein_g: int (no units)
    - fat_g: int (no units)
    - fiber_g: int (no units)
    - sodium_mg: int (no units)
    - used_knowledge_base: bool (true if this item was found using Knowledge Base recipes)

    Instructions:
    - Break down the meal into individual food items/ingredients
    - Use realistic portion sizes based on the description
    - If portion size is not specified, assume standard serving sizes
    - Include all items mentioned (main dishes, sides, beverages, condiments, etc.)
    - For prepared dishes, break down into main components when possible
    - **IMPORTANT: Only use recipes from the Knowledge Base if the meal description explicitly mentions the recipe NAME or clearly describes the complete dish. Do NOT use a recipe just because one ingredient matches.
      If Knowledge Base has multiple recipes with the same name, use the LATEST entry (the one that appears last in the text).**
    - **RECIPE INGREDIENT BREAKDOWN: When using a Knowledge Base recipe that contains multiple ingredients, list each ingredient from the recipe as a SEPARATE item in the breakdown instead of combining them into a single entry:**
      - Scale each ingredient's quantity based on the number of servings consumed vs. total servings the recipe makes
      - For example: If "1 serving pork plov" and the recipe contains "2lb pork, 1.7 cup rice, 5 mushrooms, etc." for 4 servings, then list:
        - "Pork (0.5lb)" with nutritional values for 0.5lb pork
        - "Rice (0.4 cup uncooked)" with nutritional values for ~0.4 cup rice
        - "Mushrooms (1.25 whole)" with nutritional values for ~1.25 mushrooms
        - etc.
      - Include the scaled quantity/volume of each ingredient in the item name to show exactly how much was consumed
      - Set used_knowledge_base=true for all these ingredient items
      - This makes it transparent how the nutritional calculations were derived and helps identify any errors
    - **Examples of when to use Knowledge Base recipes:**
      - "Had chicken stew" → Use chicken stew recipe, list each ingredient separately, set used_knowledge_base=true for those items
      - "Made the lasagna recipe" → Use lasagna recipe, list each ingredient separately, set used_knowledge_base=true for those items
      - "Ate leftover beef chili" → Use beef chili recipe if available, list each ingredient separately, set used_knowledge_base=true for those items
    - **Examples of when NOT to use Knowledge Base recipes:**
      - "Had 5 baby carrots" → Just count as individual carrots, don't use chicken stew recipe, set used_knowledge_base=false
      - "Cooked some rice" → Just count as rice, don't use any recipe containing rice, set used_knowledge_base=false
      - "Grilled chicken breast" → Just count as chicken, don't use recipes that contain chicken, set used_knowledge_base=false
    - If a recipe is mentioned by name but not found in the Knowledge Base, make reasonable estimates based on typical versions of that dish, set used_knowledge_base=false
    - Provide nutritional estimates based on USDA standards or common nutritional databases
    - All values should be integers (no units in the values)
    - If a nutrient value is negligible, use 0
    - Set used_knowledge_base=true only when you actually used a Knowledge Base recipe for that specific item"""
