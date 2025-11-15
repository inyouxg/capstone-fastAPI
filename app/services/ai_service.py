from ultralytics import YOLO
import os
from dotenv import load_dotenv

load_dotenv()

class FoodAIModel:
    def __init__(self):
        model_path = os.getenv("MODEL_PATH")
        if not model_path:
            raise ValueError("MODEL_PATH not found in .env")
        self.model = YOLO(model_path)


    def predict_foods(self, image_path, conf=0.2, iou=0.3):
        results = self.model(image_path, conf=conf, iou=iou)
        detected_boxes = results[0].boxes

        detected_foods = []
        for box in detected_boxes:
            cls_id = int(box.cls[0])
            cls_name = self.model.names[cls_id]
            conf_score = float(box.conf[0])
            detected_foods.append({
                "name": cls_name,
                "confidence": round(conf_score, 3)
            })
        return detected_foods
