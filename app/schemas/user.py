from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    age: int
    gender: str
    height: float
    weight: float
    activity: str

    class Config:
        orm_mode = True
