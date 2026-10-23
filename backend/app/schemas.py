from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False


class ChildCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    nickname: str | None = Field(default=None, max_length=80)
    birth_date: date
    color: str = Field(default="#d97757", pattern=r"^#[0-9a-fA-F]{6}$")


class ChildUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    nickname: str | None = Field(default=None, max_length=80)
    birth_date: date | None = None
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class ChildOut(ChildCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EntryCreate(BaseModel):
    child_ids: list[int] = Field(min_length=1)
    title: str | None = Field(default=None, max_length=120)
    kind: Literal["diary", "milestone"] = "diary"
    author: str = Field(default="家人", max_length=80)
    content: str = Field(default="", max_length=10000)
    occurred_at: datetime | None = None
    media_url: str | None = None
    media_type: Literal["image", "audio"] | None = None
    tags: str | None = None


class EntryUpdate(BaseModel):
    child_ids: list[int] | None = None
    title: str | None = Field(default=None, max_length=120)
    kind: Literal["diary", "milestone"] | None = None
    author: str | None = Field(default=None, max_length=80)
    content: str | None = Field(default=None, max_length=10000)
    occurred_at: datetime | None = None


class EntryOut(BaseModel):
    id: int
    child_ids: list[int]
    title: str | None
    kind: str
    author: str | None
    content: str | None
    occurred_at: datetime | None
    created_at: datetime
    media_url: str | None
    media_type: str | None
    tags: str | None
    model_config = ConfigDict(from_attributes=True)


class CheckupCreate(BaseModel):
    child_id: int
    checkup_date: datetime | None = None
    hospital: str | None = Field(default=None, max_length=160)
    report_text: str | None = Field(default=None, max_length=10000)
    media_url: str | None = None
    next_checkup_date: datetime | None = None
    next_checkup_notes: str | None = Field(default=None, max_length=1000)
    weight_kg: float | None = Field(default=None, gt=0, le=150)
    height_cm: float | None = Field(default=None, gt=0, le=250)
    head_cm: float | None = Field(default=None, gt=0, le=100)


class CheckupUpdate(BaseModel):
    child_id: int


class CheckupOut(BaseModel):
    id: int
    child_id: int | None
    checkup_date: datetime
    hospital: str | None
    report_text: str | None
    media_url: str | None
    abnormal_indicators: str | None
    next_checkup_date: datetime | None
    next_checkup_notes: str | None
    weight_kg: float | None
    height_cm: float | None
    head_cm: float | None
    model_config = ConfigDict(from_attributes=True)


class JaundiceCreate(BaseModel):
    child_id: int
    record_date: datetime | None = None
    value: float = Field(ge=0, le=50)
    note: str | None = Field(default=None, max_length=160)


class JaundiceUpdate(BaseModel):
    child_id: int


class JaundiceOut(BaseModel):
    id: int
    child_id: int | None
    record_date: datetime
    value: float
    note: str | None
    model_config = ConfigDict(from_attributes=True)


class GrowthCreate(BaseModel):
    child_id: int
    measured_at: datetime | None = None
    weight_kg: float | None = Field(default=None, gt=0, le=150)
    height_cm: float | None = Field(default=None, gt=0, le=250)
    head_cm: float | None = Field(default=None, gt=0, le=100)
    note: str | None = Field(default=None, max_length=300)


class GrowthOut(BaseModel):
    id: int
    child_id: int
    checkup_id: int | None
    measured_at: datetime
    weight_kg: float | None
    height_cm: float | None
    head_cm: float | None
    note: str | None
    model_config = ConfigDict(from_attributes=True)


class StoryRequest(BaseModel):
    child_ids: list[int] = Field(min_length=1)
    from_date: date | None = None
    to_date: date | None = None
    title: str | None = Field(default=None, max_length=120)
