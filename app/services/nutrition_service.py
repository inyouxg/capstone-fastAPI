import json

NUTRITION_PATH = "./app/data/food_nutrition.json"

def load_nutrition_data():
    with open(NUTRITION_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_nutrition_for_food(food_name: str):
    data = load_nutrition_data()
    return data.get(food_name)
