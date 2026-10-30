"""Validate the family growth CSV before a batch is written to the database."""

import csv
from datetime import date, datetime, time
import hashlib
import io
import math
import re


HEADERS = ["类型", "日期", "标题", "内容或备注", "记录人", "体重(kg)", "身高(cm)", "头围(cm)", "机构", "复查日期"]
MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 1000
KINDS = {"回忆": "entry", "日记": "entry", "关键时刻": "milestone", "体检": "checkup", "测量": "growth"}
METRICS = {"体重(kg)": ("weight_kg", 150), "身高(cm)": ("height_cm", 250), "头围(cm)": ("head_cm", 100)}


class ImportErrorDetails(Exception):
    def __init__(self, errors):
        self.errors = errors


def template_bytes():
    output = io.StringIO(newline="")
    csv.writer(output).writerow(HEADERS)
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def _date(value, field, errors):
    if not value:
        errors.append(f"{field}不能为空")
        return None
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        errors.append(f"{field}请写成 YYYY-MM-DD")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{field}不是有效日期")
        return None


def _metric(value, field, ceiling, errors):
    if not value:
        return None
    try:
        number = float(value)
    except ValueError:
        errors.append(f"{field}必须是数字")
        return None
    if not math.isfinite(number) or not 0 < number <= ceiling:
        errors.append(f"{field}必须大于 0 且不超过 {ceiling}")
        return None
    return number


def parse_csv(data):
    if len(data) > MAX_BYTES:
        raise ImportErrorDetails([f"文件不能超过 {MAX_BYTES // 1024 // 1024} MB"])
    try:
        content = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ImportErrorDetails(["请将文件保存为 UTF-8 编码的 CSV"])
    try:
        reader = csv.DictReader(io.StringIO(content, newline=""), strict=True)
        if reader.fieldnames != HEADERS:
            raise ImportErrorDetails(["表头与下载模板不一致；请保留全部列名和顺序"])
        records = []
        problems = []
        for line, raw in enumerate(reader, start=2):
            if None in raw:
                problems.append(f"第 {line} 行：列数超出模板")
                continue
            row = {key: (value or "").strip() for key, value in raw.items()}
            if not any(row.values()):
                continue
            if len(records) + len(problems) >= MAX_ROWS:
                raise ImportErrorDetails([f"每次最多导入 {MAX_ROWS} 条记录"])
            errors = []
            kind = KINDS.get(row["类型"])
            if not kind:
                errors.append("类型只能是回忆、关键时刻、体检或测量")
            happened = _date(row["日期"], "日期", errors)
            followup = _date(row["复查日期"], "复查日期", errors) if row["复查日期"] else None
            metrics = {name: _metric(row[label], label, ceiling, errors) for label, (name, ceiling) in METRICS.items()}
            title, note, author, hospital = (row[key] for key in ("标题", "内容或备注", "记录人", "机构"))
            if kind in ("entry", "milestone"):
                if not (title or note):
                    errors.append("回忆或关键时刻至少填写标题或内容")
                if any(value is not None for value in metrics.values()) or hospital or followup:
                    errors.append("回忆和关键时刻不能填写测量、机构或复查日期")
                if len(title) > 120 or len(note) > 10000 or len(author) > 80:
                    errors.append("标题、内容或记录人超过字数限制")
            elif kind == "checkup":
                if title or author:
                    errors.append("体检行不要填写标题或记录人")
                if not (hospital or note or any(value is not None for value in metrics.values()) or followup):
                    errors.append("体检至少填写机构、内容、测量值或复查日期")
                if len(hospital) > 160 or len(note) > 10000:
                    errors.append("机构或内容超过字数限制")
            elif kind == "growth":
                if title or author or hospital or followup:
                    errors.append("测量行不要填写标题、记录人、机构或复查日期")
                if not any(value is not None for value in metrics.values()):
                    errors.append("测量至少填写体重、身高或头围中的一项")
                if len(note) > 300:
                    errors.append("测量备注不能超过 300 字")
            if errors:
                problems.append(f"第 {line} 行：{'；'.join(errors)}")
                continue
            records.append({
                "kind": kind,
                "date": datetime.combine(happened, time(12)),
                "title": title or None,
                "note": note or None,
                "author": author or "家人",
                "hospital": hospital or None,
                "followup": datetime.combine(followup, time(12)) if followup else None,
                **metrics,
            })
        if problems:
            raise ImportErrorDetails(problems[:20] + ([f"另有 {len(problems) - 20} 行错误"] if len(problems) > 20 else []))
        if not records:
            raise ImportErrorDetails(["模板中还没有可导入的记录"])
        return records, hashlib.sha256(data).hexdigest()
    except csv.Error as error:
        raise ImportErrorDetails([f"CSV 格式无法读取：{error}"])


def import_summary(records):
    names = {"entry": "回忆", "milestone": "关键时刻", "checkup": "体检", "growth": "测量"}
    counts = {name: 0 for name in names.values()}
    for record in records:
        counts[names[record["kind"]]] += 1
    samples = [{"type": names[record["kind"]], "date": record["date"].date().isoformat(),
                "summary": (record["title"] or record["note"] or record["hospital"] or "测量数值")[:80]}
               for record in records[:8]]
    return {"total": len(records), "counts": counts, "samples": samples}
