from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date
from app.database.connection import get_db
from app.database.models.user import User

from app.services.ai_service import FoodAIModel
from app.services.nutrition_service import get_nutrition_for_food
from app.database.connection import SessionLocal
from app.database.models.meal import MealReport

router = APIRouter()

# BMR 계산 함수
def calculate_bmr(gender, weight, height, age, activity):
    if not all([gender, weight, height, age, activity]):
        return None

    if gender == "male":
        bmr = 66.47 + (13.75 * weight) + (5 * height) - (6.76 * age)
    else:
        bmr = 655.1 + (9.56 * weight) + (1.85 * height) - (4.68 * age)

    activity_factor = {
        "sedentary": 1.2,
        "low-active": 1.375,
        "active": 1.55,
        "very-active": 1.725
    }.get(activity, 1.2)

    return round(bmr * activity_factor)


@router.get("/users/main/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    # 1) 유저 정보 조회
    user = db.query(User).filter(User.completed == True).first()
    if not user:
        return {"error": "Profile not found"}

    # 2) 권장 칼로리 계산
    recommended_calories = calculate_bmr(
        user.gender, user.weight, user.height, user.age, user.activity
    )

    # 3) 오늘 식단 조회 (MealReport)
    today = date.today().strftime("%Y-%m-%d")
    today_reports = (
        db.query(MealReport)
        .filter(MealReport.date == today)
        .all()
    )

    # 4) 오늘 총 섭취량 계산
    total_calories = sum(r.total_calories for r in today_reports)
    total_carb = sum(r.macros["carbohydrate"]["value"] for r in today_reports)
    total_protein = sum(r.macros["protein"]["value"] for r in today_reports)
    total_fat = sum(r.macros["fat"]["value"] for r in today_reports)

    # 5) AMDR 기준 목표치
    carb_ratio = 0.60
    protein_ratio = 0.15
    fat_ratio = 0.25

    carb_goal = round(recommended_calories * carb_ratio / 4)
    protein_goal = round(recommended_calories * protein_ratio / 4)
    fat_goal = round(recommended_calories * fat_ratio / 9)

    # 6) progress(하루 권장 칼로리 대비 섭취율)
    progress = round((total_calories / recommended_calories) * 100) if recommended_calories else 0

    # 7) 최종 응답
    dashboard = {
        "id": user.id,
        "name": user.name,
        "date": today,
        "recommendedCalories": recommended_calories,
        "totalCalories": total_calories,
        "progress": progress,
        "macros": {
            "carbohydrate": {"value": total_carb, "goal": carb_goal, "unit": "g"},
            "protein": {"value": total_protein, "goal": protein_goal, "unit": "g"},
            "fat": {"value": total_fat, "goal": fat_goal, "unit": "g"}
        }
    }

    return dashboard



# 식단 리스트 API
    
@router.get("/meal/list")
async def get_meal_list():
    db = SessionLocal()

    today = date.today().strftime("%Y-%m-%d")

    # 오늘 날짜만 + 시간 오름차순 정렬
    reports = (
        db.query(MealReport)
        .filter(MealReport.date == today)
        .order_by(MealReport.time.asc())
        .all()
    )

    db.close()

    results = []
    for r in reports:
        results.append({
            "id": r.id,
            "time": f"{r.date}T{r.time}:00",         # dayjs 호환 ISO 포맷
            "image": f"http://localhost:8000{r.image_url}" if r.image_url else "",
            "menu": [item["name"] for item in r.items],
            "carbohydrate": r.macros["carbohydrate"]["value"],
            "protein": r.macros["protein"]["value"],
            "fat": r.macros["fat"]["value"],
            "total_calories": r.total_calories
        })

    return results
