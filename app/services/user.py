from sqlalchemy.orm import Session
from app.database.models.user import User
from app.schemas.user import UserCreate

def get_user_by_session(db: Session, session_id: str):
    return db.query(User).filter(User.session_id == session_id).first()

def create_or_update_user(db: Session, session_id: str, user_data: UserCreate):
    user = get_user_by_session(db, session_id)
    if user:
        user.name = user_data.name
        user.age = user_data.age
        user.gender = user_data.gender
        user.height = user_data.height
        user.weight = user_data.weight
        user.activity = user_data.activity
        user.completed = True
    else:
        user = User(
            session_id=session_id,
            name=user_data.name,
            age=user_data.age,
            gender=user_data.gender,
            height=user_data.height,
            weight=user_data.weight,
            activity=user_data.activity,
            completed=True,
        )
        db.add(user)

    db.commit()
    db.refresh(user)
    return user
