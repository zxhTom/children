from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from .database import Base

class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    perspective = Column(String, index=True) # 视角：daughter, son, parent, grandparent
    author = Column(String) # 记录人，比如 "妈妈", "爷爷"
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    media_url = Column(String, nullable=True) # 图片或语音的存储路径
    media_type = Column(String, nullable=True) # 'image', 'audio', 'none'
    tags = Column(String, nullable=True) # 标签，以逗号分隔，如 "健康,里程碑"

class MedicalCheckup(Base):
    __tablename__ = "medical_checkups"

    id = Column(Integer, primary_key=True, index=True)
    perspective = Column(String, index=True)
    checkup_date = Column(DateTime, default=datetime.now)
    hospital = Column(String, nullable=True)
    report_text = Column(Text, nullable=True) # 检查单OCR内容或手打内容
    media_url = Column(String, nullable=True) # 检查单照片
    # AI 提取的结构化结果预留
    abnormal_indicators = Column(Text, nullable=True) # 异常指标总结
    next_checkup_date = Column(DateTime, nullable=True) # 复查时间
    next_checkup_notes = Column(Text, nullable=True) # 复查注意事项

from sqlalchemy import Float

class JaundiceRecord(Base):
    __tablename__ = "jaundice_records"

    id = Column(Integer, primary_key=True, index=True)
    perspective = Column(String, index=True)
    record_date = Column(DateTime, default=datetime.now)
    value = Column(Float) # 黄疸值，例如 mg/dL
    note = Column(String, nullable=True) # 测量部位或备注，例如 "额头"
