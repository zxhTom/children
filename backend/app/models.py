from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import relationship

from .database import Base


entry_children = Table(
    "entry_children",
    Base.metadata,
    Column("entry_id", Integer, ForeignKey("journal_entries.id", ondelete="CASCADE"), primary_key=True),
    Column("child_id", Integer, ForeignKey("children.id", ondelete="CASCADE"), primary_key=True),
)


class Child(Base):
    __tablename__ = "children"

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    nickname = Column(String(80), nullable=True)
    birth_date = Column(Date, nullable=False)
    color = Column(String(20), nullable=False, default="#d97757")
    created_at = Column(DateTime, default=datetime.now, nullable=False)


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    perspective = Column(String, index=True)  # 保留旧数据字段
    author = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    media_url = Column(String, nullable=True)
    media_type = Column(String, nullable=True)
    tags = Column(String, nullable=True)
    title = Column(String(120), nullable=True)
    kind = Column(String(20), default="diary", nullable=False)
    occurred_at = Column(DateTime, nullable=True)
    children = relationship("Child", secondary=entry_children, lazy="selectin")

    @property
    def child_ids(self):
        return [child.id for child in self.children]


class MedicalCheckup(Base):
    __tablename__ = "medical_checkups"

    id = Column(Integer, primary_key=True, index=True)
    perspective = Column(String, index=True)  # 保留旧数据字段
    child_id = Column(Integer, ForeignKey("children.id"), index=True, nullable=True)
    checkup_date = Column(DateTime, default=datetime.now)
    hospital = Column(String, nullable=True)
    report_text = Column(Text, nullable=True)
    media_url = Column(String, nullable=True)
    abnormal_indicators = Column(Text, nullable=True)  # 历史数据兼容
    next_checkup_date = Column(DateTime, nullable=True)
    next_checkup_notes = Column(Text, nullable=True)
    weight_kg = Column(Float, nullable=True)
    height_cm = Column(Float, nullable=True)
    head_cm = Column(Float, nullable=True)


class JaundiceRecord(Base):
    __tablename__ = "jaundice_records"

    id = Column(Integer, primary_key=True, index=True)
    perspective = Column(String, index=True)  # 保留旧数据字段
    child_id = Column(Integer, ForeignKey("children.id"), index=True, nullable=True)
    record_date = Column(DateTime, default=datetime.now)
    value = Column(Float)
    note = Column(String, nullable=True)


class GrowthRecord(Base):
    __tablename__ = "growth_records"

    id = Column(Integer, primary_key=True)
    child_id = Column(Integer, ForeignKey("children.id"), index=True, nullable=False)
    checkup_id = Column(Integer, ForeignKey("medical_checkups.id"), unique=True, nullable=True)
    measured_at = Column(DateTime, nullable=False, default=datetime.now)
    weight_kg = Column(Float, nullable=True)
    height_cm = Column(Float, nullable=True)
    head_cm = Column(Float, nullable=True)
    note = Column(String(300), nullable=True)
