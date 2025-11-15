from sqlalchemy import Column, Integer, String, Float, JSON
from app.database.connection import Base

class MealReport(Base):
    __tablename__ = "meal_reports"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, nullable=False)
    time = Column(String, nullable=False)
    items = Column(JSON, nullable=False)
    total_calories = Column(Float, nullable=False)
    macros = Column(JSON, nullable=False)
    feedback = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
