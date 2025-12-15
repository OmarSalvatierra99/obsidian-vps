import calendar
from typing import Dict, List


def _month_label(period: str) -> str:
    """Return 'YYYY - Month' for a YYYY-MM period string."""
    try:
        year, month = period.split("-", 1)
        month_idx = int(month)
        return f"{year} · {calendar.month_name[month_idx][:3]}"
    except (ValueError, IndexError):
        return period or "unknown"


def _available_years(entries: List[Dict]) -> List[int]:
    years = set()
    for entry in entries:
        month = entry.get("month") or entry.get("fecha", "")
        if not month:
            continue
        try:
            years.add(int(month[:4]))
        except (ValueError, TypeError):
            continue
    return sorted(years)


def build_yearly_overview(entries: List[Dict], monthly: List[Dict], year: int) -> Dict:
    """
    Assemble aggregate insights for a given year using monthly CFDI data.

    Returns totals, filtered monthly rows, and cumulative net progress for charts.
    """
    prefix = f"{year}-"
    yearly_entries = [item for item in entries if item.get("month", "").startswith(prefix)]
    monthly_rows = [row for row in monthly if row.get("period", "").startswith(prefix)]
    monthly_rows.sort(key=lambda row: row.get("period", ""))

    totals = {
        "gross": round(sum(row.get("gross", 0.0) for row in monthly_rows), 2),
        "deductions": round(sum(row.get("deductions", 0.0) for row in monthly_rows), 2),
        "otros": round(sum(row.get("otros", 0.0) for row in monthly_rows), 2),
        "net": round(sum(row.get("net", 0.0) for row in monthly_rows), 2),
        "isr": round(sum(row.get("isr", 0.0) for row in monthly_rows), 2),
        "months": len(monthly_rows),
        "entries": len(yearly_entries),
    }
    totals["avg_net"] = round(totals["net"] / totals["months"], 2) if totals["months"] else 0.0

    progress = []
    running = 0.0
    for row in monthly_rows:
        running += row.get("net", 0.0)
        progress.append(
            {
                "period": row.get("period"),
                "label": _month_label(row.get("period", "")),
                "net": row.get("net", 0.0),
                "gross": row.get("gross", 0.0),
                "cumulative_net": round(running, 2),
            }
        )

    return {
        "year": year,
        "available_years": _available_years(entries),
        "monthly_rows": monthly_rows,
        "totals": totals,
        "progress": progress,
    }
