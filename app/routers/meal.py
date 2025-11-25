from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from datetime import datetime
import cv2, os
import numpy as np
from sqlalchemy.orm import Session

from app.services.ai_service import FoodAIModel
from app.services.nutrition_service import get_nutrition_for_food
from app.database.connection import SessionLocal
from app.database.models.meal import MealReport
from app.database.models.user import User

from app.services.feedback_loader import recommendation_detail
from app.services.nutrition_logic import (
    calculate_bmr, calculate_tdee, calculate_bmi, diff_pct,
    recommend_exercise, generate_coach_text,
    recommend_by_detail, format_substitutes
)

router = APIRouter(prefix="/meal", tags=["meal"])

# -----------------------------
# 모델 초기화
# -----------------------------
try:
    ai_model = FoodAIModel()
    print("[INFO] AI 모델 초기화 완료")
except Exception as e:
    ai_model = None
    print(f"[WARN] AI model init failed: {e}")


UPLOAD_DIR = "./app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# -----------------------------
# /meal/analyze
# -----------------------------
@router.post("/analyze")
async def analyze_meal(
    file: UploadFile = File(...),
    time: str = Form(...),
    serving: float = Form(1.0),
):

    if ai_model is None:
        raise HTTPException(
            status_code=500,
            detail="AI 모델 초기화 실패. MODEL_PATH 확인 필요."
        )

    # 1) 이미지 저장
    content = await file.read()
    if not content:
        raise HTTPException(400, "빈 파일입니다.")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(content)

    image_url = f"/static/uploads/{file.filename}"

    np_buf = np.frombuffer(content, np.uint8)
    img_bgr = cv2.imdecode(np_buf, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise HTTPException(400, "이미지를 디코드할 수 없습니다.")

    # 2) AI 예측
    detections = ai_model.predict_foods(img_bgr, conf=0.25, iou=0.45)
    if not detections:
        raise HTTPException(200, "음식을 인식하지 못했습니다.")

    dedup = {}
    for d in detections:
        name = d["name"]
        conf = d["confidence"]
        if name not in dedup or conf > dedup[name]["confidence"]:
            dedup[name] = d
    predicted_labels = list(dedup.keys())

    # 3) DB 세션 시작 (단 1회)
    db: Session = SessionLocal()

    # 유저 정보 가져오기 (단일 유저)
    user = db.query(User).filter(User.completed == True).first()
    if not user:
        db.close()
        raise HTTPException(404, "유저 정보가 없습니다.")

    sex = user.gender
    age = user.age
    height = user.height
    weight = user.weight
    activity = user.activity

    # 4) 영양 계산
    total_cal = total_carb = total_prot = total_fat = total_sugar = 0.0
    items = []

    for name in predicted_labels:
        info = get_nutrition_for_food(name)
        if info:
            cal = float(info.get("calories_kcal", 0)) * serving
            carb = float(info.get("carbohydrates_g", 0)) * serving
            prot = float(info.get("protein_g", 0)) * serving
            fat = float(info.get("fat_g", 0)) * serving
            sug = float(info.get("sugars_g", 0)) * serving

            total_cal += cal
            total_carb += carb
            total_prot += prot
            total_fat += fat
            total_sugar += sug

            items.append({"name": name, "calories": round(cal, 1)})
        else:
            items.append({"name": name, "calories": 0})

    macros = {
        "sugar": {"value": round(total_sugar, 1), "unit": "g"},
        "carbohydrate": {"value": round(total_carb, 1), "unit": "g"},
        "protein": {"value": round(total_prot, 1), "unit": "g"},
        "fat": {"value": round(total_fat, 1), "unit": "g"},
    }
    
    # ===============================================================
    # 5) 오늘 누적 섭취량 계산 (추가)
    # ===============================================================
    today = datetime.now().strftime("%Y-%m-%d")

    today_reports = (
        db.query(MealReport)
        .filter(MealReport.date == today)
        .all()
    )

    prev_total_cal = sum(r.total_calories for r in today_reports)
    prev_total_carb = sum(r.macros["carbohydrate"]["value"] for r in today_reports)
    prev_total_prot = sum(r.macros["protein"]["value"] for r in today_reports)
    prev_total_fat = sum(r.macros["fat"]["value"] for r in today_reports)
    prev_total_sugar = sum(r.macros["sugar"]["value"] for r in today_reports)

    # 오늘 총 섭취량 = 기존 누적 + 이번 식사
    day_total_cal = prev_total_cal + total_cal
    day_total_carb = prev_total_carb + total_carb
    day_total_prot = prev_total_prot + total_prot
    day_total_fat = prev_total_fat + total_fat
    day_total_sugar = prev_total_sugar + total_sugar


    # 5) AI 리포트 생성
    bmr = calculate_bmr(sex, weight, height, age)
    tdee = calculate_tdee(bmr, activity)

    recommended = {
        "calories": tdee,
        "carbohydrates": tdee * 0.60 / 4,
        "protein": tdee * 0.15 / 4,
        "fat": tdee * 0.25 / 9,
        "sugars": tdee * 0.10 / 4,
    }

    diff_pct_map = {
        "calories": diff_pct(day_total_cal, recommended["calories"]),
        "carbohydrates": diff_pct(day_total_carb, recommended["carbohydrates"]),
        "protein": diff_pct(day_total_prot, recommended["protein"]),
        "fat": diff_pct(day_total_fat, recommended["fat"]),
        "sugars": diff_pct(day_total_sugar, recommended["sugars"]),
    }

    diff_g = {
        "calories": day_total_cal - recommended["calories"],
        "carbohydrates": day_total_carb - recommended["carbohydrates"],
        "protein": day_total_prot - recommended["protein"],
        "fat": day_total_fat - recommended["fat"],
        "sugars": day_total_sugar - recommended["sugars"],
    }


    bmi, bmi_status = calculate_bmi(weight, height)
    exercise_text = recommend_exercise(diff_g["calories"], activity)

    # meal_time 분류
    meal_time = "breakfast" if time < "10:00" else \
                "lunch" if time < "15:00" else "dinner"

    substitutes = recommend_by_detail(diff_g, recommendation_detail, meal_time)
    substitute_text = format_substitutes(diff_pct_map, substitutes)

    feedback = (
        generate_coach_text(diff_pct_map, bmi, bmi_status, exercise_text)
        + "\n" + substitute_text
    )

    # 6) 시간 검증
    try:
        datetime.strptime(time, "%H:%M")
    except ValueError:
        db.close()
        raise HTTPException(400, "시간 형식 오류 (예: 08:25)")

    date_part = datetime.now().strftime("%Y-%m-%d")

    # 7) DB 저장
    report = MealReport(
        date=date_part,
        time=time,
        items=items,
        total_calories=round(total_cal, 1),
        macros=macros,
        feedback=feedback,
        image_url=image_url,
    )

    db.add(report)
    db.commit()
    db.refresh(report)
    db.close()

    return {
        "success": True,
        "meal_id": report.id,
        "image_url": image_url,
        "date": date_part,
        "meals": [{"id": report.id, "time": time, "items": items}],
        "total_calories": round(total_cal, 1),
        "macros": macros,
        "feedback": feedback,
    }


# ---------------------------------------------------
# /meal/report/{meal_id}
# ---------------------------------------------------
@router.get("/report/{meal_id}")
async def get_meal_report(meal_id: int):
    db = SessionLocal()
    report = db.query(MealReport).filter(MealReport.id == meal_id).first()
    db.close()

    if not report:
        raise HTTPException(404, "리포트를 찾을 수 없습니다.")

    return {
        "date": report.date,
        "meals": [{"id": report.id, "time": report.time, "items": report.items}],
        "total_calories": report.total_calories,
        "macros": report.macros,
        "feedback": report.feedback,
        "image_url": report.image_url,
    }
