from typing import Literal


ROUTINE_MD = {
    "push": """## PUSH
| Exercise            | Weight | Reps | Notes |
|---------------------|--------|------|-------|
| Flat Bench Press    |        |      |       |
| Incline Bench Press |        |      |       |
| Military Press      |        |      |       |
| Triceps Extensions  |        |      |       |
| Lateral Raises      |        |      |       |
""",
    "legs": """## LEGS
| Exercise             | Weight | Reps | Notes |
|----------------------|--------|------|-------|
| Leg Press            |        |      |       |
| Glute Bridge         |        |      |       |
| Romanian Deadlift    |        |      |       |
| Leg Extensions       |        |      |       |
| Standing Calf Raises |        |      |       |
| Seated Leg Curl      |        |      |       |
| Adductors Machine    |        |      |       |
""",
    "pull": """## PULL
| Exercise          | Weight | Reps | Notes |
|-------------------|--------|------|-------|
| Pull-ups          |        |      |       |
| Machine Row       |        |      |       |
| Face Pull         |        |      |       |
| Cable Biceps Curl |        |      |       |
| Reverse Curl      |        |      |       |
""",
}


def routine_markdown(kind: Literal["push", "legs", "pull", "all"] = "all") -> str:
    """Return the requested routine in markdown form."""
    if kind == "all":
        return "\n".join(ROUTINE_MD.values())
    return ROUTINE_MD.get(kind, ROUTINE_MD["push"])
