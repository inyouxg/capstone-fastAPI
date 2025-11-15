from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from datetime import datetime
import cv2, os
import numpy as np
from sqlalchemy.orm import Session

from app.services.ai_service import FoodAIModel
from app.services.nutrition_service import get_nutrition_for_food
from app.database.connection import SessionLocal
from app.database.models.meal import MealReport

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

# -----------------------------
# 업로드 이미지 저장 폴더 설정
# -----------------------------
UPLOAD_DIR = "./app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# -----------------------------
# /meal/analyze 엔드포인트
# -----------------------------
@router.post("/analyze")
async def analyze_meal(
    file: UploadFile = File(...),
    time: str = Form(...),
    serving: float = Form(1.0),
):
    """
    프론트에서 업로드한 이미지, 식사 시간(time), 섭취량(serving)을 받아
    AI 모델 예측 및 영양 계산을 수행하고 DB에 저장합니다.
    """

    # (1) AI 모델 체크
    if ai_model is None:
        raise HTTPException(
            status_code=500,
            detail="AI 모델이 초기화되지 않았습니다. MODEL_PATH 설정을 확인하세요.",
        )

    # (2) 파일 읽기 및 저장
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")

    # 파일 저장
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(content)
    image_url = f"/static/uploads/{file.filename}"

    # OpenCV로 이미지 디코딩
    np_buf = np.frombuffer(content, np.uint8)
    img_bgr = cv2.imdecode(np_buf, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise HTTPException(status_code=400, detail="이미지를 디코드할 수 없습니다.")

    # (3) AI 모델 예측 수행
    detections = ai_model.predict_foods(img_bgr, conf=0.25, iou=0.45)
    if not detections:
        raise HTTPException(status_code=200, detail="음식을 인식하지 못했습니다.")

    # 중복 라벨 제거 (confidence 높은 것만 유지)
    dedup = {}
    for d in detections:
        name = d["name"]
        conf = d["confidence"]
        if name not in dedup or conf > dedup[name]["confidence"]:
            dedup[name] = d
    predicted_labels = list(dedup.keys())

    # (4) 영양 정보 계산
    total_cal = total_carb = total_prot = total_fat = total_sugar = 0.0
    items = []
    for name in predicted_labels:
        info = get_nutrition_for_food(name)
        if info:
            cal = float(info.get("calories_kcal", 0) or 0) * serving
            carb = float(info.get("carbohydrates_g", 0) or 0) * serving
            prot = float(info.get("protein_g", 0) or 0) * serving
            fat = float(info.get("fat_g", 0) or 0) * serving
            sug = float(info.get("sugars_g", 0) or 0) * serving

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

    feedback = "하루 총 섭취량은 적정 수준입니다. 저녁에 단백질을 충분히 보충해 주세요!"

    # 시간 형식 검증
    try:
        datetime.strptime(time, "%H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="시간 형식이 올바르지 않습니다. 예: '08:25'")

    date_part = datetime.now().strftime("%Y-%m-%d")

    # DB 저장
    db: Session = SessionLocal()
    try:
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
        meal_id = report.id
    finally:
        db.close()

    # 최종 응답
    return {
        "success": True,
        "meal_id": meal_id,
        "image_url": image_url,
        "date": date_part,
        "meals": [{"id": meal_id, "time": time, "items": items}],
        "total_calories": round(total_cal, 1),
        "macros": macros,
        "feedback": feedback,
    }


# -----------------------------
# /meal/report/{meal_id} 엔드포인트
# -----------------------------
@router.get("/report/{meal_id}")
async def get_meal_report(meal_id: int):
    db = SessionLocal()
    report = db.query(MealReport).filter(MealReport.id == meal_id).first()
    db.close()

    if not report:
        raise HTTPException(status_code=404, detail="리포트를 찾을 수 없습니다.")

    return {
        "date": report.date,
        "meals": [{"id": report.id, "time": report.time, "items": report.items}],
        "total_calories": report.total_calories,
        "macros": report.macros,
        "feedback": report.feedback,
        "image_url": report.image_url,
    }
