from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
import uuid

from . import models, schemas
from .database import engine, get_db

# 创建数据库表
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="宝贝成长日记 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录用于访问上传的图片/语音
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
app.mount("/static_uploads", StaticFiles(directory=UPLOAD_DIR), name="static_uploads")

from fastapi.responses import FileResponse

# 挂载前端静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

@app.post("/api/entries", response_model=schemas.JournalEntry)
def create_entry(entry: schemas.JournalEntryCreate, db: Session = Depends(get_db)):
    db_entry = models.JournalEntry(**entry.dict())
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry

@app.get("/api/entries", response_model=List[schemas.JournalEntry])
def get_entries(perspective: Optional[str] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(models.JournalEntry)
    if perspective:
        query = query.filter(models.JournalEntry.perspective == perspective)
    entries = query.order_by(models.JournalEntry.created_at.desc()).offset(skip).limit(limit).all()
    return entries

# 文件上传接口
@app.post("/api/upload")
async def upload_media(file: UploadFile = File(...)):
    # 生成唯一文件名，防止冲突
    ext = file.filename.split('.')[-1]
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail="文件上传失败")
        
    # 根据后缀简单判断媒体类型
    media_type = "image" if ext.lower() in ['jpg', 'jpeg', 'png', 'gif', 'webp'] else "audio" if ext.lower() in ['mp3', 'wav', 'm4a', 'ogg'] else "unknown"
    
    return {
        "filename": unique_filename,
        "media_url": f"/static_uploads/{unique_filename}",
        "media_type": media_type,
        "message": "上传成功"
    }

# 预留 AI 总结接口
@app.post("/api/ai/summary")
def generate_ai_summary(perspective: str, db: Session = Depends(get_db)):
    recent_entries = db.query(models.JournalEntry).filter(
        models.JournalEntry.perspective == perspective
    ).order_by(models.JournalEntry.created_at.desc()).limit(20).all()
    
    return {
        "perspective": perspective,
        "status": "ai_placeholder",
        "summary": "这是 AI 的预留位。请在代码中配置您的 API Key 即可激活。AI 会根据最近记录自动生成本周总结哦！",
        "source_entries_count": len(recent_entries)
    }

from datetime import datetime, timedelta

@app.post("/api/checkups", response_model=schemas.MedicalCheckupSchema)
def create_checkup(checkup: schemas.MedicalCheckupCreate, db: Session = Depends(get_db)):
    # 模拟 AI 分析过程：如果用户传了图片或文字，自动进行“指标异常”和“复查时间”推断
    # TODO: 接入真实的大模型 API (如提取图片OCR、判断指标)
    
    # ---------------- 模拟 AI 处理逻辑 START ----------------
    if not checkup.abnormal_indicators and checkup.report_text:
        # 这里用简单的关键字模拟AI行为
        if "黄疸" in checkup.report_text:
            checkup.abnormal_indicators = "经血清检测，黄疸指数偏高 (预警级别: 中)"
            checkup.next_checkup_notes = "多晒太阳，多喂奶。如有嗜睡立即就医。"
            checkup.next_checkup_date = datetime.now() + timedelta(days=3)
        elif "血常规" in checkup.report_text:
            checkup.abnormal_indicators = "血红蛋白偏低，存在轻微贫血风险"
            checkup.next_checkup_notes = "建议母亲增加铁摄入，宝宝满月后复查"
            checkup.next_checkup_date = datetime.now() + timedelta(days=30)
        else:
            checkup.abnormal_indicators = "未发现明显异常指标，宝宝很健康！"
            checkup.next_checkup_notes = "按常规儿保时间进行下一次体检 (例如42天体检)"
            checkup.next_checkup_date = datetime.now() + timedelta(days=42)
    # ---------------- 模拟 AI 处理逻辑 END ----------------

    db_checkup = models.MedicalCheckup(**checkup.dict())
    db.add(db_checkup)
    db.commit()
    db.refresh(db_checkup)
    return db_checkup

@app.get("/api/checkups", response_model=List[schemas.MedicalCheckupSchema])
def get_checkups(perspective: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.MedicalCheckup)
    if perspective:
        query = query.filter(models.MedicalCheckup.perspective == perspective)
    return query.order_by(models.MedicalCheckup.checkup_date.desc()).all()

@app.post("/api/jaundice", response_model=schemas.JaundiceRecordSchema)
def create_jaundice_record(record: schemas.JaundiceRecordCreate, db: Session = Depends(get_db)):
    # 如果没有传时间，则默认当前时间
    db_record = models.JaundiceRecord(
        perspective=record.perspective,
        value=record.value,
        note=record.note,
        record_date=record.record_date or datetime.now()
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record

@app.get("/api/jaundice", response_model=List[schemas.JaundiceRecordSchema])
def get_jaundice_records(perspective: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.JaundiceRecord)
    if perspective:
        query = query.filter(models.JaundiceRecord.perspective == perspective)
    # 按照时间升序排列，方便前端画曲线图
    return query.order_by(models.JaundiceRecord.record_date.asc()).all()
