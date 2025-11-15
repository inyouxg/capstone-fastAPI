from app.services.ai_service import FoodAIModel

try:
    ai = FoodAIModel()
    print("!!모델 로드 성공!")
    print("클래스 목록:", ai.model.names)
except Exception as e:
    print("모델 로드 실패:", e)
