import datetime as dt
from typing import Dict, List


def _fmt_money(value: float) -> str:
    return f"${value:,.2f} MXN"


def compose_report(
    date: str,
    budget_summary: Dict[str, float],
    cfdi_monthly: List[Dict],
    routine_title: str,
    routine_md: str,
) -> str:
    """Create a Markdown report combining budget, CFDI, and gym routine."""
    today = date or dt.date.today().isoformat()
    lines = [
        f"# 🧾 Budget & Routine — {today}",
        f"**Income:** {_fmt_money(budget_summary['total_income'])}  ",
        f"**Expenses:** {_fmt_money(budget_summary['total_expenses'])}  ",
        f"**Debts:** {_fmt_money(budget_summary['active_debts'])}  ",
        f"**Net:** {_fmt_money(budget_summary['net_savings'])}  ",
        "",
        "---",
        "",
        "## 💰 Monthly Payroll Summary (CFDI Nómina)",
        "| Period | Gross | Deductions | Net | ISR |",
        "|---------|--------|-------------|------|------|",
    ]

    if not cfdi_monthly:
        lines.append("| - | - | - | - | - |")
    else:
        for row in cfdi_monthly:
            lines.append(
                f"| {row['period']} | {row['gross']:.2f} | {row['deductions']:.2f} | {row['net']:.2f} | {row['isr']:.2f} |"
            )

    lines.extend(
        [
            "",
            "---",
            "",
            f"## 🏋️ Today’s Routine ({routine_title})",
            routine_md.strip(),
            "",
        ]
    )

    return "\n".join(lines)
