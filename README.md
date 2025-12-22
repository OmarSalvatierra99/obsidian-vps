# Minimal Markdown Finance + Fitness Tracker

Markdown is the source of truth for expenses, income, CFDI payroll, and workouts. The CLI ingests CFDI XML, records manual entries, appends to monthly ledgers, and produces weekly/monthly reports that drop straight into Obsidian daily notes.

## Layout
- `app.py` – argparse CLI entry.
- `config.py` – paths, formats, defaults; creates `log/app.log` and data folders.
- `scripts/utils.py` – pure helpers for dates, ledger rows, CFDI parsing, workout logging, and report rendering.
- `data/ledgers/` – monthly Markdown ledgers (`YYYY-MM.md`) with `[[YYYY-MM-DD]]` links.
- `data/reports/` – generated weekly/monthly Markdown reports.
- `xml_cfdi/` – default CFDI inbox (override with `CFDI_INBOX`).
- `data/fitness/fitness-YYYY-MM.md` – monthly workout logs.
- `data/fitness/reports/monthly/` – monthly fitness reports.
- `templates/routines.md` – routine IDs (PUSH/LEGS/PULL).

## Quickstart
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py  # starts the Flask web UI on http://0.0.0.0:5000
```

The web UI works well on mobile: open `/` to log expenses/income and workouts, upload CFDI XML, and trigger markdown reports. Reports live under `data/md/` and can be downloaded from `/report/<date>/download` straight into your Obsidian vault.

## Commands
- Ingest CFDI XML and append new payroll rows:
  ```bash
  python app.py ingest-cfdi --source xml_cfdi
  ```
- Add manual income/expense/workout:
  ```bash
  python app.py add-entry --type expense --date 2025-01-17 \
    --category groceries --description "Market run" --amount 350
  ```
- Generate reports (default weekly):
  ```bash
python app.py report --period weekly --date 2025-01-17
python app.py report --period monthly --date 2025-01-01
```
- Log workouts (append to `fitness-YYYY-MM.md`):
  ```bash
  python app.py log-workout --date 2025-12-22 --day PUSH \
    --set "flat_bench_press|100|10|PR" \
    --set "military_press|40|8|" \
    --set "lateral_raises|10|15|"
  ```
- Generate fitness report:
  ```bash
  python app.py report-fitness --month 2025-12
  ```

Use `--dry-run` on any command to preview without writing. Reports are written under `data/reports/` unless `--output` is provided.

## Ledger Format
Each ledger (`data/ledgers/YYYY-MM.md`) starts with a Markdown table:
```
| date | type | category | description | amount | currency | source | uuid |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| [[2025-01-15]] | income | payroll | CFDI nómina 2025-01-01→2025-01-15 | 7736.70 | MXN | cfdi:RE2340Q2025-1-625-1E0.xml | <uuid> |
```
Expenses are stored as negative amounts; `[[YYYY-MM-DD]]` keeps entries Obsidian-friendly. UUIDs prevent double-ingestion of CFDI.

## Configuration
Override defaults with environment variables:
- `CFDI_INBOX`, `CFDI_ARCHIVE` – CFDI XML locations.
- `LEDGER_DIR`, `REPORT_DIR`, `OBSIDIAN_DAILY_DIR` – Markdown roots.
- `DEFAULT_CURRENCY` (default `MXN`), `WEEK_START` (`0` = Monday).
- `FITNESS_LOG_DIR`, `FITNESS_REPORT_DIR`, `ROUTINES_TEMPLATE` to customize fitness locations.
