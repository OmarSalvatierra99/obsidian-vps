import os
from pathlib import Path
from typing import Dict, List, Tuple


DATA_ROOT = Path(__file__).resolve().parent.parent / "data"
XML_DIR = DATA_ROOT / "xml"
MD_DIR = DATA_ROOT / "md"
SAMPLE_XML_DIR = Path(__file__).resolve().parent.parent / "xml_cfdi"


def ensure_directories() -> None:
    """Create required data directories if they do not exist."""
    for path in (DATA_ROOT, XML_DIR, MD_DIR):
        path.mkdir(parents=True, exist_ok=True)


def safe_filename(name: str) -> str:
    """Strip dangerous path parts to avoid directory traversal."""
    return os.path.basename(name)


def save_xml_file(file_storage) -> Path:
    """
    Persist an uploaded XML file into the xml directory.

    Parameters
    ----------
    file_storage : werkzeug.datastructures.FileStorage
        The uploaded file.
    """
    ensure_directories()
    filename = safe_filename(file_storage.filename or "upload.xml")
    target = XML_DIR / filename
    file_storage.save(target)
    return target


def list_xml_files() -> List[Path]:
    """Return locally available XML files from uploads and bundled samples."""
    ensure_directories()
    seen: Dict[str, Path] = {}

    if SAMPLE_XML_DIR.exists():
        for path in sorted(SAMPLE_XML_DIR.glob("*.xml")):
            seen.setdefault(path.name, path)

    for path in sorted(XML_DIR.glob("*.xml")):
        seen[path.name] = path

    return list(seen.values())


def write_report(date_slug: str, content: str) -> Path:
    """Write a markdown report for a given date (YYYY-MM-DD)."""
    ensure_directories()
    path = MD_DIR / f"{date_slug}.md"
    path.write_text(content, encoding="utf-8")
    return path


def read_report(date_slug: str) -> Tuple[str, Path]:
    """Load markdown report content for the given date."""
    ensure_directories()
    path = MD_DIR / f"{date_slug}.md"
    if not path.exists():
        raise FileNotFoundError(f"No report for {date_slug}")
    return path.read_text(encoding="utf-8"), path


def list_reports() -> List[Path]:
    """List markdown reports sorted newest first."""
    ensure_directories()
    return sorted(MD_DIR.glob("*.md"), reverse=True)
