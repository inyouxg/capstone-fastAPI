import json
import os

FEEDBACK_PATH = os.path.join("app", "data", "feedback.json")

recommendation_detail = {}

try:
    with open(FEEDBACK_PATH, "r", encoding="utf-8") as f:
        recommendation_detail = json.load(f)
    print("📁 feedback.json 로딩 완료")
except FileNotFoundError:
    print(f"⚠️ feedback.json 파일을 찾을 수 없습니다: {FEEDBACK_PATH}")
except json.JSONDecodeError:
    print("⚠️ feedback.json 형식 오류 (JSONDecodeError)")
except Exception as e:
    print(f"⚠️ feedback.json 로딩 실패: {e}")
