"""
Flask-based personal finance and fitness dashboard.

Quickstart
----------
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py

The app listens on http://0.0.0.0:5006 and stores data under ./data/:
- ./data/xml for uploaded CFDI Nómina XMLs
- ./data/md for generated daily markdown reports

Key endpoints
-------------
- GET  /health           -> {"status": "ok"}
- POST /upload-xml       -> upload CFDI files (field name: files)
- GET  /cfdi/summary     -> payroll summaries (raw + monthly)
- GET  /budget           -> budget summary using default markdown
- GET  /gym-routine      -> markdown routine (?type=push|legs|pull|all)
- POST /report           -> generate today's report (JSON body optional {"routine": "push"})
- GET  /report/<date>    -> render markdown report by date (YYYY-MM-DD)
- GET  /reports          -> list available reports
- GET  /                 -> dashboard view combining budget, CFDI, and routine
"""
import datetime as dt
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, render_template, request
from markdown_it import MarkdownIt

from src import budget
from src.cfdi_parser import parse_all_cfdi, monthly_summary
from src.gym import routine_markdown
from src.md_report import compose_report
from src.storage import (
    ensure_directories,
    list_reports,
    read_report,
    save_xml_file,
    write_report,
)


PROJECT_ROOT = Path(__file__).resolve().parent
app = Flask(
    __name__,
    template_folder=str(PROJECT_ROOT / "templates"),
    static_folder=str(PROJECT_ROOT / "static"),
)
md = MarkdownIt("commonmark")
ensure_directories()


def _current_budget(cfdi_net: Optional[float] = None):
    return budget.compute_budget_summary(md_text=budget.DEFAULT_BUDGET_MD, cfdi_net=cfdi_net)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/upload-xml", methods=["POST"])
def upload_xml():
    if "files" not in request.files:
        return jsonify({"error": "No files provided. Use form field 'files'."}), 400
    saved = []
    for file in request.files.getlist("files"):
        path = save_xml_file(file)
        saved.append(path.name)
    entries = parse_all_cfdi()
    return jsonify({"saved": saved, "parsed": entries})


@app.route("/cfdi/summary")
def cfdi_summary():
    entries = parse_all_cfdi()
    monthly = monthly_summary(entries)
    return jsonify({"entries": entries, "monthly": monthly})


@app.route("/budget")
def budget_route():
    entries = parse_all_cfdi()
    monthly = monthly_summary(entries)
    latest_net = monthly[-1]["net"] if monthly else 0.0
    summary = _current_budget(cfdi_net=latest_net)
    return jsonify(summary)


@app.route("/gym-routine")
def gym_routine():
    routine_type = request.args.get("type", "all")
    md_text = routine_markdown(routine_type)
    return jsonify({"type": routine_type, "markdown": md_text})


@app.route("/report", methods=["POST"])
def generate_report():
    routine_type = request.json.get("routine") if request.is_json else None
    routine_type = routine_type or "push"
    today = dt.date.today().isoformat()
    entries = parse_all_cfdi()
    monthly = monthly_summary(entries)
    latest_net = monthly[-1]["net"] if monthly else 0.0
    budget_summary = _current_budget(cfdi_net=latest_net)
    routine_md = routine_markdown(routine_type)
    report_md = compose_report(today, budget_summary, monthly, routine_type.upper(), routine_md)
    path = write_report(today, report_md)
    return jsonify({"date": today, "path": str(path), "markdown": report_md})


@app.route("/report/<date_slug>")
def report_view(date_slug: str):
    try:
        report_md, path = read_report(date_slug)
    except FileNotFoundError:
        return jsonify({"error": f"Report {date_slug} not found"}), 404
    html = md.render(report_md)
    return render_template("report_view.html", content=html, date=date_slug, file_path=str(path))


@app.route("/reports")
def reports():
    files = [p.name for p in list_reports()]
    return jsonify({"reports": files})


@app.route("/")
def dashboard():
    entries = parse_all_cfdi()
    monthly = monthly_summary(entries)
    latest_net = monthly[-1]["net"] if monthly else 0.0
    budget_summary = _current_budget(cfdi_net=latest_net)
    routine_md = routine_markdown("all")
    routine_html = md.render(routine_md)
    monthly_table = monthly
    return render_template(
        "dashboard.html",
        budget_summary=budget_summary,
        monthly=monthly_table,
        routine_html=routine_html,
        entries=entries,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5006, debug=True)
