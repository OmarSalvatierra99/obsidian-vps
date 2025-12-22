"""Pure helpers for dates, Markdown ledgers, CFDI parsing, and reports."""
from __future__ import annotations

import datetime as dt
import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple
from xml.etree import ElementTree as ET

import config


@dataclass(frozen=True)
class LedgerEntry:
    date: dt.date
    type: str  # income | expense | workout
    category: str
    description: str
    amount: float
    currency: str
    source: str
    uuid: str


def iso_date(value: Optional[str] = None) -> dt.date:
    """Return a date from an ISO string or today."""
    if value:
        return dt.date.fromisoformat(value)
    return dt.date.today()


def month_slug(d: dt.date) -> str:
    return f"{d.year}-{d.month:02d}"


def ledger_path_for_date(d: dt.date) -> Path:
    return config.LEDGER_DIR / f"{month_slug(d)}.md"


def _extract_uuid_from_row(line: str) -> Optional[str]:
    if not line.startswith("|") or "---" in line:
        return None
    parts = [p.strip() for p in line.strip().strip("|").split("|")]
    if len(parts) != 8:
        return None
    uuid = parts[-1]
    return uuid or None


def collect_existing_uuids(ledger_dir: Path) -> Set[str]:
    uuids: Set[str] = set()
    for path in ledger_dir.glob("*.md"):
        for line in path.read_text(encoding="utf-8").splitlines():
            uid = _extract_uuid_from_row(line)
            if uid:
                uuids.add(uid)
    return uuids


def _ensure_ledger_file(path: Path, period: dt.date) -> None:
    if path.exists():
        return
    header = f"# {month_slug(period)} Ledger\n\n## Entries\n{config.LEDGER_TABLE_HEADER}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header, encoding="utf-8")


def _format_amount(entry: LedgerEntry) -> str:
    sign_amount = entry.amount
    if entry.type == "expense" and entry.amount > 0:
        sign_amount = -entry.amount
    return f"{sign_amount:.2f}"


def ledger_row(entry: LedgerEntry) -> str:
    date_link = f"[[{entry.date.isoformat()}]]"
    return (
        f"| {date_link} | {entry.type} | {entry.category} | {entry.description} | "
        f"{_format_amount(entry)} | {entry.currency} | {entry.source} | {entry.uuid} |"
    )


def append_entries(entries: Sequence[LedgerEntry]) -> Dict[str, Path]:
    """Append entries to their monthly ledgers. Returns mapping of uuid to file path."""
    written: Dict[str, Path] = {}
    for entry in entries:
        path = ledger_path_for_date(entry.date)
        _ensure_ledger_file(path, entry.date)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(ledger_row(entry) + "\n")
        written[entry.uuid] = path
        logging.info("Appended entry %s to %s", entry.uuid, path)
    return written


def _safe_float(value: Optional[str]) -> float:
    try:
        return float(value) if value is not None else 0.0
    except ValueError:
        return 0.0


def parse_cfdi(file_path: Path, currency: str) -> LedgerEntry:
    """Normalize a CFDI (XML Nómina) file into a ledger entry."""
    ns = {
        "cfdi": "http://www.sat.gob.mx/cfd/4",
        "tfd": "http://www.sat.gob.mx/TimbreFiscalDigital",
        "nomina12": "http://www.sat.gob.mx/nomina12",
    }
    tree = ET.parse(file_path)
    root = tree.getroot()

    tfd = root.find(".//tfd:TimbreFiscalDigital", ns)
    uuid = (tfd.attrib.get("UUID") if tfd is not None else None) or hashlib.sha1(
        file_path.name.encode("utf-8")
    ).hexdigest()

    issued = root.attrib.get("Fecha", "")[:10]
    issued_date = iso_date(issued) if issued else iso_date()

    nomina = root.find(".//nomina12:Nomina", ns)
    pay_date = iso_date(nomina.attrib.get("FechaPago")) if nomina is not None and nomina.attrib.get("FechaPago") else issued_date
    period_start = nomina.attrib.get("FechaInicialPago") if nomina is not None else None
    period_end = nomina.attrib.get("FechaFinalPago") if nomina is not None else None
    percep_total = _safe_float(nomina.attrib.get("TotalPercepciones") if nomina is not None else None)
    deduc_total = _safe_float(nomina.attrib.get("TotalDeducciones") if nomina is not None else None)
    total = _safe_float(root.attrib.get("Total"))

    net = percep_total - deduc_total if percep_total else total - deduc_total
    desc_period = f"{period_start or issued_date}→{period_end or issued_date}"
    description = f"CFDI nómina {desc_period}"

    return LedgerEntry(
        date=pay_date,
        type="income",
        category="payroll",
        description=description,
        amount=round(net, 2),
        currency=currency,
        source=f"cfdi:{file_path.name}",
        uuid=uuid,
    )


def ingest_cfdi_files(
    cfdi_dir: Path, currency: str, existing_uuids: Set[str]
) -> List[LedgerEntry]:
    entries: List[LedgerEntry] = []
    for file_path in sorted(cfdi_dir.glob("*.xml")):
        try:
            entry = parse_cfdi(file_path, currency)
        except ET.ParseError as exc:
            logging.warning("Skip %s (parse error: %s)", file_path.name, exc)
            continue
        if entry.uuid in existing_uuids:
            logging.info("Skip %s (duplicate UUID %s)", file_path.name, entry.uuid)
            continue
        entries.append(entry)
        existing_uuids.add(entry.uuid)
    return entries


def manual_entry(
    date_str: Optional[str],
    entry_type: str,
    category: str,
    description: str,
    amount: float,
    currency: str,
    source: str = "manual",
    uuid: Optional[str] = None,
) -> LedgerEntry:
    date_obj = iso_date(date_str)
    amt = amount if entry_type != "expense" else -abs(amount)
    uid = uuid or hashlib.sha1(f"{date_obj.isoformat()}-{description}-{amt}".encode("utf-8")).hexdigest()
    return LedgerEntry(
        date=date_obj,
        type=entry_type,
        category=category,
        description=description,
        amount=round(amt, 2),
        currency=currency,
        source=source,
        uuid=uid,
    )


def _parse_row_to_entry(line: str) -> Optional[LedgerEntry]:
    if not line.startswith("|") or "---" in line:
        return None
    parts = [p.strip() for p in line.strip().strip("|").split("|")]
    if len(parts) != 8:
        return None
    date_raw = parts[0]
    if date_raw.startswith("[[") and date_raw.endswith("]]"):
        date_raw = date_raw[2:-2]
    try:
        date_obj = iso_date(date_raw)
    except ValueError:
        return None
    try:
        amount = float(parts[4])
    except ValueError:
        amount = 0.0
    return LedgerEntry(
        date=date_obj,
        type=parts[1],
        category=parts[2],
        description=parts[3],
        amount=amount,
        currency=parts[5],
        source=parts[6],
        uuid=parts[7],
    )


def load_entries_from_dir(ledger_dir: Path) -> List[LedgerEntry]:
    entries: List[LedgerEntry] = []
    for path in ledger_dir.glob("*.md"):
        for line in path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_row_to_entry(line)
            if parsed:
                entries.append(parsed)
    return entries


def filter_entries(
    entries: Iterable[LedgerEntry], start: dt.date, end: dt.date
) -> List[LedgerEntry]:
    return [
        e for e in entries
        if start <= e.date <= end
    ]


def summarize(entries: Sequence[LedgerEntry]) -> Dict[str, float]:
    income = sum(e.amount for e in entries if e.amount > 0)
    expenses = sum(e.amount for e in entries if e.amount < 0)
    workouts = len([e for e in entries if e.type == "workout"])
    net = income + expenses
    return {
        "income": round(income, 2),
        "expenses": round(abs(expenses), 2),
        "net": round(net, 2),
        "workouts": workouts,
    }


def weekly_range(anchor: dt.date, week_start: int) -> tuple[dt.date, dt.date]:
    delta = (anchor.weekday() - week_start) % 7
    start = anchor - dt.timedelta(days=delta)
    end = start + dt.timedelta(days=6)
    return start, end


def monthly_range(anchor: dt.date) -> tuple[dt.date, dt.date]:
    start = anchor.replace(day=1)
    if start.month == 12:
        next_month = start.replace(year=start.year + 1, month=1, day=1)
    else:
        next_month = start.replace(month=start.month + 1, day=1)
    end = next_month - dt.timedelta(days=1)
    return start, end


def render_report(title: str, entries: Sequence[LedgerEntry], start: dt.date, end: dt.date) -> str:
    totals = summarize(entries)
    lines = [
        f"# {title}",
        f"**Period:** {start.isoformat()} → {end.isoformat()}",
        "",
        "## Totals",
        f"- income: {totals['income']:.2f} {config.DEFAULT_CURRENCY}",
        f"- expenses: {totals['expenses']:.2f} {config.DEFAULT_CURRENCY}",
        f"- net: {totals['net']:.2f} {config.DEFAULT_CURRENCY}",
        f"- workouts: {totals['workouts']}",
        "",
        "## Entries",
    ]
    for entry in sorted(entries, key=lambda e: (e.date, e.type, e.uuid)):
        sign = "+" if entry.amount >= 0 else "-"
        abs_amount = abs(entry.amount)
        lines.append(
            f"- [[{entry.date.isoformat()}]] {entry.type} | {entry.category} | "
            f"{entry.description} | {sign}{abs_amount:.2f} {entry.currency} | {entry.source} | {entry.uuid}"
        )
    if not entries:
        lines.append("- (no entries)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Fitness routines and logging
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkoutSet:
    date: dt.date
    day: str  # PUSH/LEGS/PULL
    exercise_id: str
    weight_raw: str
    reps: int
    notes: str
    weight: Optional[float] = None


ALL_EXERCISES: Set[str] = {eid for group in config.ROUTINES.values() for eid in group}


def validate_exercise(exercise_id: str) -> None:
    if exercise_id not in ALL_EXERCISES:
        raise ValueError(f"Unknown exercise_id '{exercise_id}'")


def parse_set_str(raw: str, date: dt.date, day: str) -> WorkoutSet:
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) != 4:
        raise ValueError("Set must be 'exercise|weight|reps|notes'")
    exercise_id, weight_raw, reps_raw, notes = parts
    validate_exercise(exercise_id)
    weight_clean = weight_raw.lower()
    weight_val = None
    if weight_clean not in ("bw", ""):
        try:
            weight_val = float(weight_raw)
        except ValueError as exc:
            raise ValueError(f"Invalid weight '{weight_raw}'") from exc
    try:
        reps_val = int(reps_raw)
    except ValueError as exc:
        raise ValueError(f"Invalid reps '{reps_raw}'") from exc
    return WorkoutSet(
        date=date,
        day=day.upper(),
        exercise_id=exercise_id,
        weight_raw=weight_raw,
        reps=reps_val,
        notes=notes,
        weight=weight_val,
    )


def fitness_log_path(date: dt.date) -> Path:
    return config.FITNESS_LOG_DIR / f"fitness-{date.year:04d}-{date.month:02d}.md"


def append_workout(date: dt.date, day: str, sets: Sequence[WorkoutSet]) -> Path:
    path = fitness_log_path(date)
    if not path.exists():
        path.write_text(f"# Fitness {date.year:04d}-{date.month:02d}\n\n", encoding="utf-8")
    lines = [f"## {date.isoformat()} — {day.upper()}"]
    for s in sets:
        lines.append(f"- {s.exercise_id} | {s.weight_raw} | {s.reps} | {s.notes}")
    with path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n\n")
    logging.info("Logged %s sets to %s", len(sets), path)
    return path


def _parse_workout_line(line: str) -> Optional[Tuple[str, str, int, str]]:
    if not line.startswith("- "):
        return None
    parts = [p.strip() for p in line[2:].split("|")]
    if len(parts) != 4:
        return None
    exercise_id, weight_raw, reps_raw, notes = parts
    try:
        reps_val = int(reps_raw)
    except ValueError:
        return None
    return exercise_id, weight_raw, reps_val, notes


def load_workouts(path: Path) -> List[WorkoutSet]:
    workouts: List[WorkoutSet] = []
    if not path.exists():
        return workouts
    date: Optional[dt.date] = None
    day = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("## "):
            heading = line[3:]
            try:
                date_str, day_label = [p.strip() for p in heading.split("—")]
                date = iso_date(date_str)
                day = day_label
            except Exception:
                date = None
                continue
            continue
        parsed = _parse_workout_line(line)
        if parsed and date:
            exercise_id, weight_raw, reps_val, notes = parsed
            weight_val = None
            if weight_raw.lower() not in ("bw", ""):
                try:
                    weight_val = float(weight_raw)
                except ValueError:
                    weight_val = None
            workouts.append(
                WorkoutSet(
                    date=date,
                    day=day,
                    exercise_id=exercise_id,
                    weight_raw=weight_raw,
                    reps=reps_val,
                    notes=notes,
                    weight=weight_val,
                )
            )
    return workouts


def best_sets(workouts: Sequence[WorkoutSet]) -> Dict[str, WorkoutSet]:
    best: Dict[str, WorkoutSet] = {}
    for ws in workouts:
        if ws.weight is None:
            continue
        est_1rm = ws.weight * (1 + ws.reps / 30)
        current = best.get(ws.exercise_id)
        if current is None:
            best[ws.exercise_id] = ws
            continue
        current_est = current.weight * (1 + current.reps / 30) if current.weight is not None else 0
        if est_1rm > current_est:
            best[ws.exercise_id] = ws
    return best


def pr_history(workouts: Sequence[WorkoutSet]) -> List[WorkoutSet]:
    history: List[WorkoutSet] = []
    best_by_ex: Dict[str, float] = {}
    for ws in sorted(workouts, key=lambda x: (x.date, x.exercise_id)):
        if ws.weight is None:
            continue
        est = ws.weight * (1 + ws.reps / 30)
        prev = best_by_ex.get(ws.exercise_id, 0.0)
        if est > prev:
            history.append(ws)
            best_by_ex[ws.exercise_id] = est
    return history


def summarize_workouts(workouts: Sequence[WorkoutSet]) -> Dict[str, Dict[str, float]]:
    stats: Dict[str, Dict[str, float]] = {}
    for ws in workouts:
        if ws.exercise_id not in stats:
            stats[ws.exercise_id] = {
                "max_weight": 0.0,
                "max_reps": 0,
                "best_est_1rm": 0.0,
            }
        if ws.weight is not None:
            stats[ws.exercise_id]["max_weight"] = max(stats[ws.exercise_id]["max_weight"], ws.weight)
            est = ws.weight * (1 + ws.reps / 30)
            stats[ws.exercise_id]["best_est_1rm"] = max(stats[ws.exercise_id]["best_est_1rm"], est)
        stats[ws.exercise_id]["max_reps"] = max(stats[ws.exercise_id]["max_reps"], ws.reps)
    return stats


def render_fitness_report(month: str, workouts: Sequence[WorkoutSet]) -> str:
    best = best_sets(workouts)
    prs = pr_history(workouts)
    lines = [f"# Fitness Report — {month}", ""]

    lines.append("## PRs")
    if prs:
        for ws in prs:
            est = ws.weight * (1 + ws.reps / 30) if ws.weight is not None else 0
            weight_label = f"{ws.weight_raw}kg" if ws.weight is not None else ws.weight_raw
            lines.append(
                f"- {ws.exercise_id}: {weight_label} x {ws.reps} (Est 1RM ~ {est:.1f}kg) — {ws.date.isoformat()}"
            )
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Top Stats")
    lines.append("| Exercise | Best Set | Best Weight | Best Reps | Est 1RM |")
    lines.append("|---|---:|---:|---:|---:|")
    for exercise in sorted(ALL_EXERCISES):
        ws = best.get(exercise)
        if ws and ws.weight is not None:
            est = ws.weight * (1 + ws.reps / 30)
            best_set = f"{ws.weight:.0f}kg x {ws.reps}"
            best_weight = f"{ws.weight:.0f}"
            best_reps = f"{ws.reps}"
            est_str = f"{est:.1f}"
        else:
            best_set = "-"
            best_weight = "-"
            best_reps = "-"
            est_str = "-"
        lines.append(f"| {exercise} | {best_set} | {best_weight} | {best_reps} | {est_str} |")

    if not workouts:
        lines.append("\n_No workouts logged for this period._")
    return "\n".join(lines)
