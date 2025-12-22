import json
import re
from typing import Dict, List, Optional


DEFAULT_BUDGET_MD = """## Income
- Salary: $8,994.54 MXN

## Fixed expenses
- Said 🐻♥️: $3,000 MXN
- Food & Transport: $1,500 MXN
- Motorcycle 🏍️: $1,132 MXN
- Manillar 🚲: $110 MXN
- Tarjeta 🤖: $310 MXN
- Banamex 🏦: $2,182 MXN
- Vero ♥️: $150 MXN
- Gym 💪: $200 MXN
- Copel 🔰: $240 MXN

## Active Debts
- Luis: $200 MXN
"""


def _extract_amount(text: str) -> float:
    match = re.search(r"([-+]?\\d+[\\d.,]*)", text.replace(",", ""))
    return float(match.group(1)) if match else 0.0


def parse_budget_markdown(md_text: str) -> Dict[str, List[Dict]]:
    """
    Parse a lightweight markdown budget format into sections.

    Supports headings like "## Income" followed by "- Label: $123 MXN" lines.
    """
    sections = {"income": [], "fixed_expenses": [], "active_debts": []}
    current_section = None
    for line in md_text.splitlines():
        line = line.strip()
        if line.lower().startswith("## income"):
            current_section = "income"
            continue
        if line.lower().startswith("## fixed"):
            current_section = "fixed_expenses"
            continue
        if line.lower().startswith("## active"):
            current_section = "active_debts"
            continue
        if line.startswith("-") and current_section:
            parts = line[1:].split(":", 1)
            label = parts[0].strip()
            amount_text = parts[1] if len(parts) > 1 else "0"
            amount = _extract_amount(amount_text)
            sections[current_section].append({"label": label, "amount": amount})
    return sections


def parse_budget_json(raw: str) -> Dict[str, List[Dict]]:
    data = json.loads(raw)
    return {
        "income": data.get("income", []),
        "fixed_expenses": data.get("fixed_expenses", []),
        "active_debts": data.get("active_debts", []),
    }


def compute_budget_summary(
    md_text: Optional[str] = None, cfdi_net: Optional[float] = None
) -> Dict[str, float]:
    """Compute totals for income, expenses, debts, and balances."""
    if md_text is None:
        md_text = DEFAULT_BUDGET_MD
    sections = parse_budget_markdown(md_text)
    total_income = sum(item["amount"] for item in sections["income"])
    total_expenses = sum(item["amount"] for item in sections["fixed_expenses"])
    active_debts = sum(item["amount"] for item in sections["active_debts"])
    net_savings = total_income - total_expenses - active_debts
    monthly_cfdi_net = cfdi_net if cfdi_net is not None else 0.0
    effective_balance = monthly_cfdi_net - total_expenses
    return {
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "active_debts": round(active_debts, 2),
        "net_savings": round(net_savings, 2),
        "monthly_cfdi_net": round(monthly_cfdi_net, 2),
        "effective_balance": round(effective_balance, 2),
        "sections": sections,
    }
