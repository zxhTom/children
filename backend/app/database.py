from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 使用 SQLite，数据将保存在当前目录的 children_diary.db 文件中
SQLALCHEMY_DATABASE_URL = "sqlite:///./children_diary.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 依赖项，用于在 FastAPI 路由中获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
