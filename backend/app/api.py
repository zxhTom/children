import calendar
from collections import OrderedDict
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models, schemas
from .database import get_db

router = APIRouter(prefix="/api")


def require_child(db: Session, child_id: int) -> models.Child:
    child = db.get(models.Child, child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="宝宝档案不存在")
    return child


def require_children(db: Session, child_ids: list[int]) -> list[models.Child]:
    unique_ids = list(dict.fromkeys(child_ids))
    if not unique_ids:
        raise HTTPException(status_code=422, detail="请选择至少一个宝宝")
    children = db.query(models.Child).filter(models.Child.id.in_(unique_ids)).all()
    if len(children) != len(unique_ids):
        raise HTTPException(status_code=422, detail="所选宝宝档案不存在")
    by_id = {child.id: child for child in children}
    return [by_id[child_id] for child_id in unique_ids]


def require_measurement(weight, height, head):
    if all(value is None for value in (weight, height, head)):
        raise HTTPException(status_code=422, detail="至少填写一项生长测量数据")


@router.get("/children", response_model=list[schemas.ChildOut])
def list_children(db: Session = Depends(get_db)):
    return db.query(models.Child).order_by(models.Child.birth_date.desc(), models.Child.id).all()


@router.post("/children", response_model=schemas.ChildOut)
def create_child(payload: schemas.ChildCreate, db: Session = Depends(get_db)):
    child = models.Child(**payload.model_dump())
    db.add(child)
    db.commit()
    db.refresh(child)
    return child


@router.patch("/children/{child_id}", response_model=schemas.ChildOut)
def update_child(child_id: int, payload: schemas.ChildUpdate, db: Session = Depends(get_db)):
    child = require_child(db, child_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is None and key in ("name", "birth_date", "color"):
            raise HTTPException(status_code=422, detail=f"{key} 不能为空")
        setattr(child, key, value)
    db.commit()
    db.refresh(child)
    return child


@router.get("/entries", response_model=list[schemas.EntryOut])
def list_entries(
    child_id: int | None = None,
    unassigned: bool = False,
    kind: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(models.JournalEntry)
    if child_id is not None:
        require_child(db, child_id)
        query = query.join(models.entry_children).filter(models.entry_children.c.child_id == child_id)
    elif unassigned:
        query = query.filter(~models.JournalEntry.children.any())
    if kind:
        query = query.filter(models.JournalEntry.kind == kind)
    return query.order_by(func.coalesce(models.JournalEntry.occurred_at, models.JournalEntry.created_at).desc(), models.JournalEntry.id.desc()).offset(skip).limit(limit).all()


@router.post("/entries", response_model=schemas.EntryOut)
def create_entry(payload: schemas.EntryCreate, db: Session = Depends(get_db)):
    children = require_children(db, payload.child_ids)
    if not any((payload.title, payload.content.strip(), payload.media_url)):
        raise HTTPException(status_code=422, detail="请填写标题、内容或上传素材")
    data = payload.model_dump(exclude={"child_ids"})
    data["occurred_at"] = data["occurred_at"] or datetime.now()
    entry = models.JournalEntry(**data, children=children)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.patch("/entries/{entry_id}", response_model=schemas.EntryOut)
def update_entry(entry_id: int, payload: schemas.EntryUpdate, db: Session = Depends(get_db)):
    entry = db.get(models.JournalEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    updates = payload.model_dump(exclude_unset=True)
    if "child_ids" in updates:
        entry.children = require_children(db, updates.pop("child_ids"))
    for key, value in updates.items():
        if key in ("kind", "author", "content") and value is None:
            raise HTTPException(status_code=422, detail=f"{key} 不能为空")
        setattr(entry, key, value)
    if any(key in updates for key in ("title", "content", "media_url")) and not any(
        (entry.title and entry.title.strip(), entry.content and entry.content.strip(), entry.media_url)
    ):
        raise HTTPException(status_code=422, detail="请保留标题、内容或素材")
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/checkups", response_model=list[schemas.CheckupOut])
def list_checkups(child_id: int | None = None, unassigned: bool = False, db: Session = Depends(get_db)):
    query = db.query(models.MedicalCheckup)
    if child_id is not None:
        require_child(db, child_id)
        query = query.filter(models.MedicalCheckup.child_id == child_id)
    elif unassigned:
        query = query.filter(models.MedicalCheckup.child_id.is_(None))
    return query.order_by(models.MedicalCheckup.checkup_date.desc()).all()


@router.post("/checkups", response_model=schemas.CheckupOut)
def create_checkup(payload: schemas.CheckupCreate, db: Session = Depends(get_db)):
    require_child(db, payload.child_id)
    data = payload.model_dump()
    data["checkup_date"] = data["checkup_date"] or datetime.now()
    checkup = models.MedicalCheckup(**data)
    db.add(checkup)
    db.flush()
    if any(data[key] is not None for key in ("weight_kg", "height_cm", "head_cm")):
        db.add(models.GrowthRecord(
            child_id=payload.child_id, checkup_id=checkup.id, measured_at=checkup.checkup_date,
            weight_kg=payload.weight_kg, height_cm=payload.height_cm, head_cm=payload.head_cm,
            note=payload.hospital,
        ))
    db.commit()
    db.refresh(checkup)
    return checkup


@router.patch("/checkups/{checkup_id}", response_model=schemas.CheckupOut)
def update_checkup(checkup_id: int, payload: schemas.CheckupUpdate, db: Session = Depends(get_db)):
    checkup = db.get(models.MedicalCheckup, checkup_id)
    if checkup is None:
        raise HTTPException(status_code=404, detail="体检记录不存在")
    updates = payload.model_dump(exclude_unset=True)
    if "child_id" in updates:
        if updates["child_id"] is None:
            raise HTTPException(status_code=422, detail="宝宝不能为空")
        require_child(db, updates["child_id"])
    if "checkup_date" in updates and updates["checkup_date"] is None:
        raise HTTPException(status_code=422, detail="体检日期不能为空")
    for key, value in updates.items():
        setattr(checkup, key, value)
    growth = db.query(models.GrowthRecord).filter_by(checkup_id=checkup.id).first()
    has_measurement = any(getattr(checkup, key) is not None for key in ("weight_kg", "height_cm", "head_cm"))
    if growth and (not has_measurement or checkup.child_id is None):
        db.delete(growth)
    elif has_measurement and checkup.child_id is not None:
        if growth is None:
            growth = models.GrowthRecord(checkup_id=checkup.id)
            db.add(growth)
        growth.child_id = checkup.child_id
        growth.measured_at = checkup.checkup_date
        growth.weight_kg = checkup.weight_kg
        growth.height_cm = checkup.height_cm
        growth.head_cm = checkup.head_cm
        growth.note = checkup.hospital
    db.commit()
    db.refresh(checkup)
    return checkup


@router.get("/jaundice", response_model=list[schemas.JaundiceOut])
def list_jaundice(child_id: int | None = None, unassigned: bool = False, db: Session = Depends(get_db)):
    query = db.query(models.JaundiceRecord)
    if child_id is not None:
        require_child(db, child_id)
        query = query.filter(models.JaundiceRecord.child_id == child_id)
    elif unassigned:
        query = query.filter(models.JaundiceRecord.child_id.is_(None))
    return query.order_by(models.JaundiceRecord.record_date.asc()).all()


@router.post("/jaundice", response_model=schemas.JaundiceOut)
def create_jaundice(payload: schemas.JaundiceCreate, db: Session = Depends(get_db)):
    require_child(db, payload.child_id)
    data = payload.model_dump()
    data["record_date"] = data["record_date"] or datetime.now()
    record = models.JaundiceRecord(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.patch("/jaundice/{record_id}", response_model=schemas.JaundiceOut)
def update_jaundice(record_id: int, payload: schemas.JaundiceUpdate, db: Session = Depends(get_db)):
    record = db.get(models.JaundiceRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="黄疸记录不存在")
    updates = payload.model_dump(exclude_unset=True)
    if "child_id" in updates:
        if updates["child_id"] is None:
            raise HTTPException(status_code=422, detail="宝宝不能为空")
        require_child(db, updates["child_id"])
    for key in ("record_date", "value"):
        if key in updates and updates[key] is None:
            raise HTTPException(status_code=422, detail=f"{key} 不能为空")
    for key, value in updates.items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


@router.get("/growth", response_model=list[schemas.GrowthOut])
def list_growth(child_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(models.GrowthRecord)
    if child_id is not None:
        require_child(db, child_id)
        query = query.filter(models.GrowthRecord.child_id == child_id)
    return query.order_by(models.GrowthRecord.measured_at.asc()).all()


@router.post("/growth", response_model=schemas.GrowthOut)
def create_growth(payload: schemas.GrowthCreate, db: Session = Depends(get_db)):
    require_child(db, payload.child_id)
    require_measurement(payload.weight_kg, payload.height_cm, payload.head_cm)
    data = payload.model_dump()
    data["measured_at"] = data["measured_at"] or datetime.now()
    record = models.GrowthRecord(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.patch("/growth/{record_id}", response_model=schemas.GrowthOut)
def update_growth(record_id: int, payload: schemas.GrowthUpdate, db: Session = Depends(get_db)):
    record = db.get(models.GrowthRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="测量记录不存在")
    if record.checkup_id is not None:
        raise HTTPException(status_code=409, detail="这条测量来自体检，请编辑对应的体检记录")
    updates = payload.model_dump(exclude_unset=True)
    if "child_id" in updates:
        if updates["child_id"] is None:
            raise HTTPException(status_code=422, detail="宝宝不能为空")
        require_child(db, updates["child_id"])
    if "measured_at" in updates and updates["measured_at"] is None:
        raise HTTPException(status_code=422, detail="测量日期不能为空")
    for key, value in updates.items():
        setattr(record, key, value)
    require_measurement(record.weight_kg, record.height_cm, record.head_cm)
    db.commit()
    db.refresh(record)
    return record


VISIT_MONTHS = (1, 3, 6, 8, 12, 18, 24, 30, 36, 48, 60, 72)


def add_months(birth: date, months: int) -> date:
    year = birth.year + (birth.month - 1 + months) // 12
    month = (birth.month - 1 + months) % 12 + 1
    return date(year, month, min(birth.day, calendar.monthrange(year, month)[1]))


@router.get("/children/{child_id}/visits")
def visit_plan(child_id: int, db: Session = Depends(get_db)):
    child = require_child(db, child_id)
    checkups = db.query(models.MedicalCheckup).filter_by(child_id=child_id).all()
    today = date.today()
    plan = []
    for months in VISIT_MONTHS:
        due = add_months(child.birth_date, months)
        tolerance = 45 if months <= 12 else 70 if months <= 36 else 180
        matched = min(
            (record for record in checkups if abs((record.checkup_date.date() - due).days) <= tolerance),
            key=lambda record: abs((record.checkup_date.date() - due).days), default=None,
        )
        status = "recorded" if matched else "upcoming" if due > today else "pending"
        plan.append({
            "months": months, "label": f"{months // 12}岁" if months >= 48 else f"{months}月龄",
            "due_date": due.isoformat(), "status": status,
            "checkup_id": matched.id if matched else None,
        })
    return {"child_id": child_id, "visits": plan}


def age_text(birth: date, event: date) -> str:
    if event < birth:
        return "出生前"
    months = (event.year - birth.year) * 12 + event.month - birth.month - (event.day < birth.day)
    if months < 1:
        return f"出生第{(event - birth).days + 1}天"
    if months < 12:
        return f"{months}个月"
    return f"{months // 12}岁" + (f"{months % 12}个月" if months % 12 else "")


MOMENT_WORDS = ("第一次", "首次", "学会", "生日", "第一颗牙", "翻身", "入园", "毕业", "会走", "会说")


@router.get("/moments/suggestions")
def moment_suggestions(child_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(models.JournalEntry).filter(models.JournalEntry.kind == "diary")
    if child_id is not None:
        require_child(db, child_id)
        query = query.join(models.entry_children).filter(models.entry_children.c.child_id == child_id)
    candidates = []
    for entry in query.order_by(models.JournalEntry.created_at.desc()).limit(300).all():
        text_value = f"{entry.title or ''} {entry.content or ''}"
        matched = next((word for word in MOMENT_WORDS if word in text_value), None)
        if matched:
            candidates.append({
                "id": entry.id, "title": entry.title or "一段成长日记",
                "excerpt": (entry.content or "")[:120],
                "occurred_at": (entry.occurred_at or entry.created_at).isoformat(),
                "child_ids": entry.child_ids, "reason": f"记录中提到了“{matched}”",
            })
        if len(candidates) >= 8:
            break
    return candidates


@router.post("/stories/generate")
def generate_story(payload: schemas.StoryRequest, db: Session = Depends(get_db)):
    children = require_children(db, payload.child_ids)
    if payload.from_date and payload.to_date and payload.from_date > payload.to_date:
        raise HTTPException(status_code=422, detail="起始日期不能晚于结束日期")
    query = db.query(models.JournalEntry).join(models.entry_children).filter(
        models.entry_children.c.child_id.in_([child.id for child in children])
    ).distinct()
    timestamp = func.coalesce(models.JournalEntry.occurred_at, models.JournalEntry.created_at)
    if payload.from_date:
        query = query.filter(timestamp >= datetime.combine(payload.from_date, datetime.min.time()))
    if payload.to_date:
        query = query.filter(timestamp < datetime.combine(payload.to_date + timedelta(days=1), datetime.min.time()))
    entries = query.order_by(timestamp.asc(), models.JournalEntry.id.asc()).limit(300).all()
    selected_ids = [child.id for child in children]
    growth_query = db.query(models.GrowthRecord).filter(models.GrowthRecord.child_id.in_(selected_ids))
    checkup_query = db.query(models.MedicalCheckup).filter(models.MedicalCheckup.child_id.in_(selected_ids))
    if payload.from_date:
        start = datetime.combine(payload.from_date, datetime.min.time())
        growth_query = growth_query.filter(models.GrowthRecord.measured_at >= start)
        checkup_query = checkup_query.filter(models.MedicalCheckup.checkup_date >= start)
    if payload.to_date:
        end = datetime.combine(payload.to_date + timedelta(days=1), datetime.min.time())
        growth_query = growth_query.filter(models.GrowthRecord.measured_at < end)
        checkup_query = checkup_query.filter(models.MedicalCheckup.checkup_date < end)
    growth_records = growth_query.order_by(models.GrowthRecord.measured_at.asc()).all()
    checkups = checkup_query.all()
    health_notes = []
    for child in children:
        measurements = [record for record in growth_records if record.child_id == child.id]
        child_checkups = [record for record in checkups if record.child_id == child.id]
        if measurements or child_checkups:
            latest = measurements[-1] if measurements else None
            health_notes.append({
                "child_id": child.id, "name": child.nickname or child.name,
                "checkups": len(child_checkups), "measurements": len(measurements),
                "latest": ({"date": latest.measured_at.date().isoformat(),
                            "weight_kg": latest.weight_kg, "height_cm": latest.height_cm,
                            "head_cm": latest.head_cm} if latest else None),
            })
    selected = {child.id: child for child in children}
    sections = OrderedDict()
    for entry in entries:
        moment_date = (entry.occurred_at or entry.created_at).date()
        period = f"{moment_date.year}年{moment_date.month}月"
        involved = [selected[child.id] for child in entry.children if child.id in selected]
        card = {
            "id": entry.id,
            "date": moment_date.isoformat(),
            "title": entry.title or ("关键时刻" if entry.kind == "milestone" else "成长日记"),
            "kind": entry.kind,
            "content": entry.content or "",
            "author": entry.author or "家人",
            "media_url": entry.media_url,
            "media_type": entry.media_type,
            "children": [{"id": child.id, "name": child.nickname or child.name,
                          "age": age_text(child.birth_date, moment_date)} for child in involved],
            "shared": len(entry.children) > 1,
        }
        sections.setdefault(period, []).append(card)
    count = len(entries)
    milestone_count = sum(entry.kind == "milestone" for entry in entries)
    names = "、".join(child.nickname or child.name for child in children)
    summary = (f"{names}留下了{count}段成长记录，其中{milestone_count}个被标记为关键时刻。"
               if count else f"{names}还没有这段时间的成长日记。")
    if checkups or growth_records:
        summary += f"手册中还有{len(checkups)}次体检、{len(growth_records)}次测量。"
    return {
        "title": payload.title or (f"{names}的成长故事" if len(children) == 1 else "我们的家庭成长故事"),
        "summary": summary,
        "generated_at": datetime.now().isoformat(),
        "from_date": payload.from_date.isoformat() if payload.from_date else None,
        "to_date": payload.to_date.isoformat() if payload.to_date else None,
        "children": [{"id": child.id, "name": child.name, "nickname": child.nickname,
                      "birth_date": child.birth_date.isoformat()} for child in children],
        "stats": {"records": count, "milestones": milestone_count,
                  "photos": sum(entry.media_type == "image" for entry in entries),
                  "shared": sum(len(entry.children) > 1 for entry in entries),
                  "checkups": len(checkups), "measurements": len(growth_records)},
        "health_notes": health_notes,
        "sections": [{"period": period, "moments": cards} for period, cards in sections.items()],
    }
