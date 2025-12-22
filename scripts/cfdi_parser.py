import calendar
import datetime as dt
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .storage import list_xml_files


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _parse_float(value: Optional[str]) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def parse_cfdi_file(path: Path) -> Dict:
    """
    Parse a CFDI Nómina XML file into a normalized dictionary.

    The parser focuses on Nomina 1.2 within CFDI 4.0 documents and
    degrades gracefully when optional nodes are missing.
    """
    tree = ET.parse(path)
    root = tree.getroot()

    def find_first(elem: ET.Element, name: str) -> Optional[ET.Element]:
        for child in elem.iter():
            if _local_name(child.tag).lower() == name.lower():
                return child
        return None

    emisor = find_first(root, "Emisor")
    receptor = find_first(root, "Receptor")
    nomina = find_first(root, "Nomina")

    fecha = root.attrib.get("Fecha") or (nomina.attrib.get("FechaPago") if nomina is not None else "")
    fecha_pago = ""
    periodicidad = ""
    total_percepciones = total_deducciones = total_otros = 0.0
    isr = 0.0
    percepciones_breakdown: List[Dict] = []
    deducciones_breakdown: List[Dict] = []

    if nomina is not None:
        fecha_pago = nomina.attrib.get("FechaPago", "") or fecha
        periodicidad = nomina.attrib.get("PeriodicidadPago", "")
        total_percepciones = _parse_float(nomina.attrib.get("TotalPercepciones"))
        total_deducciones = _parse_float(nomina.attrib.get("TotalDeducciones"))
        total_otros = _parse_float(nomina.attrib.get("TotalOtrosPagos"))

        percepciones = find_first(nomina, "Percepciones")
        if percepciones is not None:
            for p in percepciones:
                if _local_name(p.tag) != "Percepcion":
                    continue
                percepciones_breakdown.append(
                    {
                        "tipo": p.attrib.get("TipoPercepcion"),
                        "concepto": p.attrib.get("Concepto"),
                        "importe_gravado": _parse_float(p.attrib.get("ImporteGravado")),
                        "importe_exento": _parse_float(p.attrib.get("ImporteExento")),
                    }
                )

        deducciones = find_first(nomina, "Deducciones")
        if deducciones is not None:
            for d in deducciones:
                if _local_name(d.tag) != "Deduccion":
                    continue
                importe = _parse_float(d.attrib.get("Importe"))
                if d.attrib.get("TipoDeduccion") == "002":
                    isr = importe
                deducciones_breakdown.append(
                    {
                        "tipo": d.attrib.get("TipoDeduccion"),
                        "concepto": d.attrib.get("Concepto"),
                        "importe": importe,
                    }
                )

    neto = total_percepciones - total_deducciones + total_otros
    month = ""
    if fecha_pago:
        try:
            month = fecha_pago[:7]
            fecha = dt.datetime.fromisoformat(fecha_pago).date().isoformat()
        except ValueError:
            month = fecha_pago[:7]

    return {
        "archivo": path.name,
        "fecha": fecha,
        "month": month,
        "version": root.attrib.get("Version", ""),
        "emisor": emisor.attrib.get("Nombre", "") if emisor is not None else "",
        "receptor": receptor.attrib.get("Nombre", "") if receptor is not None else "",
        "total_percepciones": total_percepciones,
        "total_deducciones": total_deducciones,
        "total_otros": total_otros,
        "neto": neto,
        "isr": isr,
        "periodicidad": periodicidad,
        "percepciones": percepciones_breakdown,
        "deducciones": deducciones_breakdown,
    }


def parse_all_cfdi(paths: Optional[Iterable[Path]] = None) -> List[Dict]:
    """Parse all provided CFDI XML paths (defaults to stored XMLs)."""
    files = list(paths) if paths is not None else list_xml_files()
    summaries: List[Dict] = []
    for path in files:
        try:
            summaries.append(parse_cfdi_file(path))
        except Exception as exc:  # pragma: no cover - runtime feedback via app
            summaries.append({"archivo": path.name, "error": str(exc)})
    return summaries


def monthly_summary(entries: List[Dict]) -> List[Dict]:
    """Aggregate CFDI entries by month."""
    totals = defaultdict(lambda: {"gross": 0.0, "deductions": 0.0, "otros": 0.0, "net": 0.0, "isr": 0.0})
    for item in entries:
        month = item.get("month") or "unknown"
        agg = totals[month]
        agg["gross"] += item.get("total_percepciones", 0.0)
        agg["deductions"] += item.get("total_deducciones", 0.0)
        agg["otros"] += item.get("total_otros", 0.0)
        agg["net"] += item.get("neto", 0.0)
        agg["isr"] += item.get("isr", 0.0)
    formatted = []
    for month, agg in sorted(totals.items()):
        formatted.append(
            {
                "period": month,
                "gross": round(agg["gross"], 2),
                "deductions": round(agg["deductions"], 2),
                "otros": round(agg["otros"], 2),
                "net": round(agg["net"], 2),
                "isr": round(agg["isr"], 2),
            }
        )
    return formatted


def biweekly_summary(entries: List[Dict]) -> List[Dict]:
    """Aggregate CFDI entries by quincena (1-15 and 16-end of month)."""
    totals = defaultdict(lambda: {"gross": 0.0, "deductions": 0.0, "otros": 0.0, "net": 0.0, "isr": 0.0})

    for item in entries:
        fecha = item.get("fecha") or ""
        try:
            paid = dt.date.fromisoformat(fecha)
        except (TypeError, ValueError):
            continue
        half = 1 if paid.day <= 15 else 2
        key = (paid.year, paid.month, half)
        agg = totals[key]
        agg["gross"] += item.get("total_percepciones", 0.0)
        agg["deductions"] += item.get("total_deducciones", 0.0)
        agg["otros"] += item.get("total_otros", 0.0)
        agg["net"] += item.get("neto", 0.0)
        agg["isr"] += item.get("isr", 0.0)

    formatted = []
    for (year, month, half) in sorted(totals.keys()):
        agg = totals[(year, month, half)]
        start_day = 1 if half == 1 else 16
        end_day = 15 if half == 1 else calendar.monthrange(year, month)[1]
        label = f"{year}-{month:02d} {'1a' if half == 1 else '2a'} quincena"
        formatted.append(
            {
                "period": f"{year}-{month:02d}-Q{half}",
                "label": label,
                "range": f"{year}-{month:02d}-{start_day:02d} · {year}-{month:02d}-{end_day:02d}",
                "gross": round(agg["gross"], 2),
                "deductions": round(agg["deductions"], 2),
                "otros": round(agg["otros"], 2),
                "net": round(agg["net"], 2),
                "isr": round(agg["isr"], 2),
            }
        )

    return formatted
