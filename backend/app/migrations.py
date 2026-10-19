"""Small, repeatable SQLite migration for the original single-view database."""

from datetime import date, datetime
from pathlib import Path
import sqlite3

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from . import models
from .database import engine


NEW_COLUMNS = {
    "journal_entries": {
        "title": "VARCHAR(120)",
        "kind": "VARCHAR(20) DEFAULT 'diary'",
        "occurred_at": "DATETIME",
    },
    "medical_checkups": {
        "child_id": "INTEGER",
        "weight_kg": "FLOAT",
        "height_cm": "FLOAT",
        "head_cm": "FLOAT",
    },
    "jaundice_records": {"child_id": "INTEGER"},
}


def _backup_legacy_database():
    path = Path(engine.url.database or "").resolve()
    if not path.is_file():
        return
    with sqlite3.connect(path) as source:
        version = source.execute("PRAGMA user_version").fetchone()[0]
        has_data = source.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='journal_entries'"
        ).fetchone()
        if version or not has_data:
            return
        backup = path.with_name(f"{path.name}.pre-multichild-{datetime.now():%Y%m%d%H%M%S}.bak")
        with sqlite3.connect(backup) as target:
            source.backup(target)


def initialize_database():
    _backup_legacy_database()
    models.Base.metadata.create_all(bind=engine)

    with engine.begin() as connection:
        inspector = inspect(connection)
        for table, definitions in NEW_COLUMNS.items():
            present = {column["name"] for column in inspector.get_columns(table)}
            for name, definition in definitions.items():
                if name not in present:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))
        version = connection.execute(text("PRAGMA user_version")).scalar()

    if version >= 1:
        return

    with Session(engine) as db:
        if not db.query(models.Child).first():
            db.add_all([
                models.Child(name="张希悦", nickname="妹妹", birth_date=date(2026, 9, 20), color="#d97757"),
                models.Child(name="张希哲", nickname="哥哥", birth_date=date(2020, 9, 26), color="#6b82a8"),
            ])
            db.flush()
        children = {child.name: child for child in db.query(models.Child).all()}
        by_view = {"daughter": children.get("张希悦"), "son": children.get("张希哲")}
        for entry in db.query(models.JournalEntry).all():
            child = by_view.get(entry.perspective)
            if child and child not in entry.children:
                entry.children.append(child)
        for model in (models.MedicalCheckup, models.JaundiceRecord):
            for record in db.query(model).filter(model.child_id.is_(None)).all():
                child = by_view.get(record.perspective)
                if child:
                    record.child_id = child.id
        db.commit()

    with engine.begin() as connection:
        connection.execute(text("PRAGMA user_version = 1"))
