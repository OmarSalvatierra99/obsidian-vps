from pathlib import Path
from typing import Dict, List, Literal


PROJECT_ROOT = Path(__file__).resolve().parent.parent
GYM_MD_PATH = PROJECT_ROOT / "gym.md"

DEFAULT_ROUTINE_MD = {
    "push": """## PUSH
| Exercise              | Weight | Reps | Notes |
|-----------------------|--------|------|-------|
| Flat Bench Press      |        |      |       |
| Incline Bench Press   |        |      |       |
| Military Press        |        |      |       |
| Triceps Extensions    |        |      |       |
| Lateral Raises        |        |      |       |
""",
    "legs": """## LEGS
| Exercise               | Weight | Reps | Notes |
|------------------------|--------|------|-------|
| Leg Press              |        |      |       |
| Glute Bridge           |        |      |       |
| Romanian Deadlift      |        |      |       |
| Leg Extensions         |        |      |       |
| Standing Calf Raises   |        |      |       |
| Seated Leg Curl        |        |      |       |
| Adductors Machine      |        |      |       |
""",
    "pull": """## PULL
| Exercise               | Weight | Reps | Notes |
|------------------------|--------|------|-------|
| Pull-ups               |        |      |       |
| Machine Row            |        |      |       |
| Face Pull              |        |      |       |
| Cable Biceps Curl      |        |      |       |
| Reverse Bicep Curl     |        |      |       |
""",
}


def _parse_gym_sections(md_text: str) -> Dict[str, str]:
    """Split gym.md content into sections keyed by lowercase routine name."""
    sections: Dict[str, str] = {}
    current_key = None
    buffer: List[str] = []

    for raw_line in md_text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("## "):
            if current_key and buffer:
                sections[current_key] = "\n".join(buffer).strip() + "\n"
            header = line.strip()
            current_key = header[3:].strip().lower()
            buffer = [header]
        elif current_key:
            buffer.append(line)

    if current_key and buffer:
        sections[current_key] = "\n".join(buffer).strip() + "\n"

    normalized: Dict[str, str] = {}
    for key, value in sections.items():
        normalized[key] = value if value.endswith("\n") else value + "\n"
    return normalized


def _load_routines() -> Dict[str, str]:
    if not GYM_MD_PATH.exists():
        return DEFAULT_ROUTINE_MD.copy()
    try:
        content = GYM_MD_PATH.read_text(encoding="utf-8")
    except OSError:
        return DEFAULT_ROUTINE_MD.copy()
    sections = _parse_gym_sections(content)
    if not sections:
        return DEFAULT_ROUTINE_MD.copy()
    merged = DEFAULT_ROUTINE_MD.copy()
    merged.update(sections)
    return merged


ROUTINE_MD = _load_routines()


def routine_markdown(kind: Literal["push", "legs", "pull", "all"] = "all") -> str:
    """Return the requested routine in markdown form."""
    if kind == "all":
        return "\n".join(ROUTINE_MD.values())
    return ROUTINE_MD.get(kind, ROUTINE_MD["push"])
