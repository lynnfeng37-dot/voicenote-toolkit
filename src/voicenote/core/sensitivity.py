"""Deterministic sensitive-entity detection for correction policy escalation."""

from __future__ import annotations

import re

SENSITIVE_CATEGORIES = frozenset(
    {
        "number",
        "percentage",
        "date",
        "company_name",
        "personal_name",
        "ticker_symbol",
        "valuation_multiple",
        "financial_metric",
        "currency",
        "money",
    }
)

_ARABIC_NUMBER = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:[.,]\d+)?")
_CHINESE_NUMBER = re.compile(r"[零〇一二两三四五六七八九十百千万亿兆]+")
_PERCENTAGE = re.compile(
    r"(?:%|％|百分之|百分点|基点|bps?\b)",  # noqa: RUF001 - valid transcript data
    re.IGNORECASE,
)
_DATE = re.compile(
    r"(?:\b\d{4}[-/.年]\d{1,2}(?:[-/.月]\d{1,2}日?)?|\b\d{1,2}[:：]\d{2}\b)"  # noqa: RUF001
)
_TICKER = re.compile(r"(?:\b[A-Z]{1,6}\b|\b\d{5,6}\.(?:SH|SZ|HK)\b)")
_VALUATION = re.compile(r"(?:\bP/?E\b|\bP/?B\b|EV/?EBITDA|倍)", re.IGNORECASE)
_MONEY = re.compile(r"(?:[$¥￥€£]|美元|人民币|港元|亿元|万元)")


def is_sensitive_correction(
    original: str,
    corrected: str,
    category: str,
    configured_categories: tuple[str, ...] = (),
) -> bool:
    """Return true when either local patterns or category policy require stricter thresholds."""

    normalized_category = category.strip().lower()
    sensitive_categories = SENSITIVE_CATEGORIES | {
        item.strip().lower() for item in configured_categories
    }
    if normalized_category in sensitive_categories:
        return True
    combined = f"{original}\n{corrected}"
    return any(
        pattern.search(combined) is not None
        for pattern in (
            _ARABIC_NUMBER,
            _CHINESE_NUMBER,
            _PERCENTAGE,
            _DATE,
            _TICKER,
            _VALUATION,
            _MONEY,
        )
    )

