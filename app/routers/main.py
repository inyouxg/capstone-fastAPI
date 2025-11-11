from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date
from app.database.connection import get_db
from app.database.models.user import User

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


# 메인 대시보드 API
@router.get("/users/main/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    user = db.query(User).filter(User.completed == True).first()
    if not user:
        return {"error": "Profile not found"}

    recommended_calories = calculate_bmr(
        user.gender, user.weight, user.height, user.age, user.activity
    )
    
    # AMDR 평균 비율 적용
    carb_ratio = 0.60
    protein_ratio = 0.15
    fat_ratio = 0.25

    # 권장 영양소 계산
    carb_goal = round(recommended_calories * carb_ratio / 4)
    protein_goal = round(recommended_calories * protein_ratio / 4)
    fat_goal = round(recommended_calories * fat_ratio / 9)


    dashboard = {
        "id": user.id,
        "name": user.name,
        "date": str(date.today()),
        "recommendedCalories": recommended_calories,
        "totalCalories": 0,  # AI 연동 전, 일단 0
        "progress": 0,       # 진행률도 일단 0
        "macros": {
            "carbohydrate": {"value": 0, "goal": carb_goal, "unit": "g"},
            "protein": {"value": 0, "goal": protein_goal, "unit": "g"},
            "fat": {"value": 0, "goal": fat_goal, "unit": "g"}
        }
    }

    return dashboard


# 식단 리스트 API (AI 연동 전, 비워둠)
@router.get("/users/main/diet")
def get_diet():
    return []
