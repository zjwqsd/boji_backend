from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import DATABASE_URL

# 连接数据库
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 依赖注入数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
