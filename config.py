"""Central configuration for the Markdown-first finance + fitness tracker."""
from __future__ import annotations

import os
from pathlib import Path

# Base paths
BASE_DIR: Path = Path(__file__).resolve().parent
DATA_DIR: Path = BASE_DIR / "data"
LOG_DIR: Path = BASE_DIR / "log"
TEMPLATES_DIR: Path = BASE_DIR / "templates"
STATIC_DIR: Path = BASE_DIR / "static"

# Domain directories
CFDI_INBOX: Path = Path(os.getenv("CFDI_INBOX", BASE_DIR / "xml_cfdi"))
CFDI_ARCHIVE: Path = Path(os.getenv("CFDI_ARCHIVE", DATA_DIR / "xml"))
LEDGER_DIR: Path = Path(os.getenv("LEDGER_DIR", DATA_DIR / "ledgers"))
REPORT_DIR: Path = Path(os.getenv("REPORT_DIR", DATA_DIR / "reports"))
OBSIDIAN_DAILY_DIR: Path = Path(os.getenv("OBSIDIAN_DAILY_DIR", DATA_DIR / "daily"))

# Fitness
FITNESS_LOG_DIR: Path = Path(os.getenv("FITNESS_LOG_DIR", DATA_DIR / "fitness"))
FITNESS_REPORT_DIR: Path = Path(os.getenv("FITNESS_REPORT_DIR", DATA_DIR / "fitness/reports/monthly"))
ROUTINES_TEMPLATE: Path = Path(os.getenv("ROUTINES_TEMPLATE", BASE_DIR / "templates" / "routines.md"))
ROUTINES = {
    "PUSH": [
        "flat_bench_press",
        "incline_bench_press",
        "military_press",
        "triceps_extensions",
        "lateral_raises",
    ],
    "LEGS": [
        "leg_press",
        "glute_bridge",
        "romanian_deadlift",
        "leg_extensions",
        "standing_calf_raises",
        "seated_leg_curl",
        "adductors_machine",
    ],
    "PULL": [
        "pull_ups",
        "machine_row",
        "face_pull",
        "cable_biceps_curl",
        "reverse_bicep_curl",
    ],
}

# Files
LOG_FILE: Path = LOG_DIR / "app.log"

# Formats and defaults
DATE_FORMAT: str = "%Y-%m-%d"
DEFAULT_CURRENCY: str = os.getenv("DEFAULT_CURRENCY", "MXN")
WEEK_START: int = int(os.getenv("WEEK_START", "0"))  # 0=Monday
LEDGER_TABLE_HEADER = (
    "| date | type | category | description | amount | currency | source | uuid |\n"
    "| --- | --- | --- | --- | ---: | --- | --- | --- |\n"
)


def ensure_directories() -> None:
    """Create required directories and placeholder log file."""
    for path in (
        DATA_DIR,
        LOG_DIR,
        CFDI_INBOX,
        CFDI_ARCHIVE,
        LEDGER_DIR,
        REPORT_DIR,
        OBSIDIAN_DAILY_DIR,
        FITNESS_LOG_DIR,
        FITNESS_REPORT_DIR,
        ROUTINES_TEMPLATE.parent,
    ):
        path.mkdir(parents=True, exist_ok=True)
    LOG_FILE.touch(exist_ok=True)
