from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.connection import Base, engine
from app.routers import user, main, meal

app = FastAPI()

#쿠키 기반 인증을 위한 CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 프론트 주소 정확히 기입하기!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#라우터 등록
app.include_router(user.router)
app.include_router(main.router)
app.include_router(meal.router)

#DB 테이블 생성 (미들웨어와 라우터 등록 이후)
Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"message": "FastAPI server is running 🚀"}


app.mount("/static", StaticFiles(directory="app/static"), name="static")
