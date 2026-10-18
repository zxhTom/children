from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class JournalEntryBase(BaseModel):
    perspective: str
    author: str
    content: str
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    tags: Optional[str] = None

class JournalEntryCreate(JournalEntryBase):
    pass

class JournalEntry(JournalEntryBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class MedicalCheckupBase(BaseModel):
    perspective: str
    hospital: Optional[str] = None
    report_text: Optional[str] = None
    media_url: Optional[str] = None
    abnormal_indicators: Optional[str] = None
    next_checkup_date: Optional[datetime] = None
    next_checkup_notes: Optional[str] = None

class MedicalCheckupCreate(MedicalCheckupBase):
    pass

class MedicalCheckupSchema(MedicalCheckupBase):
    id: int
    checkup_date: datetime

    class Config:
        orm_mode = True

class JaundiceRecordBase(BaseModel):
    perspective: str
    value: float
    note: Optional[str] = None
    record_date: Optional[datetime] = None

class JaundiceRecordCreate(JaundiceRecordBase):
    pass

class JaundiceRecordSchema(JaundiceRecordBase):
    id: int
    record_date: datetime

    class Config:
        orm_mode = True
