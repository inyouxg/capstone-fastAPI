from fastapi import APIRouter, Depends, Request, Response, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.schemas.user import UserCreate
from app.services.user import create_or_update_user, get_user_by_session
import uuid

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/auth/anonymous")
def create_anonymous_session(request: Request, response: Response):
    existing_session = request.cookies.get("session_id")
    if existing_session:
        # 이미 세션 쿠키가 있으면 새로 만들지 않음
        return {"success": True, "session_id": existing_session}

    session_id = str(uuid.uuid4())
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=False,
        samesite="Lax",
    )
    return {"success": True, "session_id": session_id}


#프로필 저장
@router.put("/profile")
def update_profile(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="No session cookie")

    user = create_or_update_user(db, session_id, user_data)
    return {"success": True, "user_id": user.id}


#프로필 상태 확인
@router.get("/profile/status")
def get_profile_status(request: Request, db: Session = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="No session cookie")

    user = get_user_by_session(db, session_id)
    return {"completed": bool(user and user.completed)}
