"""Flask web service for the Markdown-first finance + fitness tracker."""
from __future__ import annotations

import datetime as dt
import logging
import os
from pathlib import Path
from typing import Dict, Iterable, List

from flask import Flask, abort, jsonify, redirect, render_template, request, send_file, url_for
from markupsafe import Markup
from werkzeug.utils import secure_filename
import markdown2

import config
from scripts import budget, cfdi_parser, earnings, gym, md_report, storage, utils


def setup_logging() -> None:
    """Configure logging to file + stdout for web context."""
    config.ensure_directories()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handlers = [
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler(),
    ]
    logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=handlers)
    for handler in logging.getLogger().handlers:
        handler.setFormatter(formatter)


app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY", "dev-secret")
markdown = markdown2.Markdown(extras=["tables", "fenced-code-blocks", "strike"])

config.ensure_directories()
storage.ensure_directories()
setup_logging()


def _render_markdown(md_text: str) -> str:
    """Convert Markdown to HTML for safe template rendering."""
    return markdown.convert(md_text or "")


def _latest_report_slug() -> str | None:
    reports = storage.list_reports()
    return reports[0].stem if reports else None


def _budget_summary_from_cfdi(monthly: List[Dict]) -> Dict[str, float]:
    latest_net = monthly[-1]["net"] if monthly else 0.0
    return budget.compute_budget_summary(cfdi_net=latest_net)


def _save_uploaded_files(files: Iterable, target_dir: Path) -> List[str]:
    saved: List[str] = []
    target_dir.mkdir(parents=True, exist_ok=True)
    for file_storage in files:
        if not getattr(file_storage, "filename", ""):
            continue
        filename = secure_filename(file_storage.filename)
        dest = target_dir / filename
        file_storage.save(dest)
        saved.append(filename)
    return saved


@app.context_processor
def inject_globals() -> Dict[str, str]:
    return {
        "environment_label": os.getenv("APP_ENV", "local"),
        "server_port": os.getenv("PORT", "5000"),
    }


@app.get("/")
def dashboard():
    entries = cfdi_parser.parse_all_cfdi()
    monthly = cfdi_parser.monthly_summary(entries)
    budget_summary = _budget_summary_from_cfdi(monthly)
    routine_html = Markup(_render_markdown(gym.routine_markdown("all")))
    today = dt.date.today().isoformat()
    return render_template(
        "dashboard.html",
        entries=entries,
        monthly=monthly,
        budget_summary=budget_summary,
        routine_html=routine_html,
        latest_report=_latest_report_slug(),
        today=today,
        status=request.args.get("status"),
        message=request.args.get("message"),
    )


@app.get("/reports")
def reports():
    report_paths = storage.list_reports()
    reports_view = [
        {
            "name": path.stem,
            "display_date": path.stem,
            "size_kb": round(path.stat().st_size / 1024, 1),
            "link": url_for("report_view", date_slug=path.stem),
        }
        for path in report_paths
    ]
    return render_template("reports.html", reports=reports_view)


@app.get("/report/<date_slug>")
def report_view(date_slug: str):
    try:
        md_content, path = storage.read_report(date_slug)
    except FileNotFoundError:
        abort(404)
    html = Markup(_render_markdown(md_content))
    return render_template("report_view.html", date=date_slug, file_path=path, content=html)


@app.get("/report/<date_slug>/download")
def download_report(date_slug: str):
    try:
        _, path = storage.read_report(date_slug)
    except FileNotFoundError:
        abort(404)
    return send_file(path, as_attachment=True, download_name=f"{date_slug}.md")


@app.post("/report")
def generate_report():
    payload = request.get_json(silent=True) or {}
    date_slug = payload.get("date") or dt.date.today().isoformat()
    routine = (payload.get("routine") or "all").lower()
    routine_label = routine.title() if routine in ("push", "pull", "legs") else "All"

    cfdi_entries = cfdi_parser.parse_all_cfdi()
    monthly = cfdi_parser.monthly_summary(cfdi_entries)
    budget_summary = _budget_summary_from_cfdi(monthly)

    report_md = md_report.compose_report(
        date_slug,
        budget_summary=budget_summary,
        cfdi_monthly=monthly,
        routine_title=routine_label,
        routine_md=gym.routine_markdown(routine if routine in ("push", "pull", "legs") else "all"),
    )
    path = storage.write_report(date_slug, report_md)
    logging.info("Report %s written to %s", date_slug, path)
    return jsonify({"date": date_slug, "link": url_for("report_view", date_slug=date_slug)})


@app.post("/upload-xml")
def upload_xml():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No XML files provided"}), 400
    saved = _save_uploaded_files(files, config.CFDI_INBOX)

    existing = utils.collect_existing_uuids(config.LEDGER_DIR)
    new_entries = utils.ingest_cfdi_files(config.CFDI_INBOX, config.DEFAULT_CURRENCY, existing)
    written = utils.append_entries(new_entries) if new_entries else {}

    return jsonify(
        {
            "saved": saved,
            "ingested": len(new_entries),
            "ledgers": [str(path) for path in written.values()],
        }
    )


def _safe_float(raw: str | None, default: float = 0.0) -> float:
    try:
        return float(raw) if raw not in (None, "") else default
    except ValueError:
        return default


@app.post("/entries")
def create_entry():
    data = request.get_json(silent=True) or request.form
    entry = utils.manual_entry(
        date_str=data.get("date") or None,
        entry_type=data.get("type", "expense"),
        category=data.get("category", "general"),
        description=data.get("description", "").strip() or "entry",
        amount=_safe_float(data.get("amount"), 0.0),
        currency=data.get("currency") or config.DEFAULT_CURRENCY,
        source="web",
        uuid=None,
    )
    utils.append_entries([entry])
    logging.info("Recorded web entry %s", entry.uuid)
    if request.is_json:
        return jsonify({"status": "ok", "uuid": entry.uuid})
    return redirect(url_for("dashboard", status="ok", message="Entry saved"))


@app.post("/workouts")
def log_workout():
    data = request.get_json(silent=True) or request.form
    date = utils.iso_date(data.get("date"))
    day = (data.get("day") or "PUSH").upper()
    raw_sets = data.get("sets") or ""

    if isinstance(raw_sets, str):
        set_lines = [line.strip() for line in raw_sets.splitlines() if line.strip()]
    elif isinstance(raw_sets, list):
        set_lines = [str(item).strip() for item in raw_sets if str(item).strip()]
    else:
        set_lines = []

    if not set_lines:
        return jsonify({"error": "No sets provided"}), 400

    sets = [utils.parse_set_str(raw, date, day) for raw in set_lines]
    path = utils.append_workout(date, day, sets)
    logging.info("Logged %s sets for %s", len(sets), date)
    if request.is_json:
        return jsonify({"status": "ok", "path": str(path)})
    return redirect(url_for("dashboard", status="ok", message="Workout saved"))


@app.get("/earnings")
def earnings_default():
    entries = cfdi_parser.parse_all_cfdi()
    monthly = cfdi_parser.monthly_summary(entries)
    year = dt.date.today().year
    overview = earnings.build_yearly_overview(entries, monthly, year)
    return render_template("earnings.html", year=year, overview=overview)


@app.get("/earnings/<int:year>")
def earnings_by_year(year: int):
    entries = cfdi_parser.parse_all_cfdi()
    monthly = cfdi_parser.monthly_summary(entries)
    overview = earnings.build_yearly_overview(entries, monthly, year)
    return render_template("earnings.html", year=year, overview=overview)


@app.get("/income")
def income_report():
    entries = cfdi_parser.parse_all_cfdi()
    totals = {
        "files": len(entries),
        "net": round(sum(item.get("neto", 0.0) for item in entries), 2),
        "gross": round(sum(item.get("total_percepciones", 0.0) for item in entries), 2),
        "avg_net": round(sum(item.get("neto", 0.0) for item in entries) / len(entries), 2) if entries else 0.0,
        "quincenas": len(entries),
    }
    monthly = cfdi_parser.monthly_summary(entries)
    last_payment = monthly[-1]["period"] if monthly else ""
    quincenas = cfdi_parser.biweekly_summary(entries)
    xml_files = [path.name for path in storage.list_xml_files()] if hasattr(storage, "list_xml_files") else []
    return render_template(
        "income_report.html",
        totals=totals,
        quincenas=quincenas,
        last_payment=last_payment,
        xml_files=xml_files,
    )


@app.get("/health")
def health():
    return jsonify({"status": "ok", "now": dt.datetime.utcnow().isoformat()})


def main() -> None:
    port = int(os.getenv("PORT", "5005"))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG") == "1")


if __name__ == "__main__":
    main()
