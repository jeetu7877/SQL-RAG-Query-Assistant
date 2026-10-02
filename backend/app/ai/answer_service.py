"""Deterministic natural-language answers (no extra Gemini call -> saves quota)."""
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

_NOUN = re.compile(
    r"how many ([a-z_ ]+?)(?: are| were| is| was| do| does| did| have| has| exist| in| per| placed| ordered|\?|$)",
    re.I,
)


def _fmt(value: Any) -> str:
    if isinstance(value, bool) or value is None:
        return str(value)
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, (float, Decimal)):
        return f"{float(value):,.2f}"
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def build_answer(question: str, columns: list[str], rows: list[list[Any]], truncated: bool) -> str:
    if not rows:
        return "No matching rows were found for that question."

    if len(rows) == 1 and len(columns) == 1:
        value = rows[0][0]
        m = _NOUN.search(question)
        if m and isinstance(value, int):
            return f"There are {_fmt(value)} {m.group(1).strip()}."
        return f"{columns[0].replace('_', ' ').capitalize()}: {_fmt(value)}."

    n = len(rows)
    top = re.search(r"\btop\s+(\d+)", question, re.I)
    if top and int(top.group(1)) == n:
        text = f"Here are the top {n} results."
    elif n == 1:
        text = "Here is the matching row."
    else:
        text = f"Here are the {n} matching rows."
    if truncated:
        text += " Results were limited; refine your question to see fewer, more specific rows."
    return text
