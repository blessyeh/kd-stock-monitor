#!/usr/bin/env python3
"""
Data Quality — three-state verification framework for the Taiwan market
risk-monitoring data sources (TWSE margin/institutional, TAIFEX futures,
CBC FX, FRED FX).

Per spec (KD_Stock_Monitor_市場風險監控規格.docx, 第三章):
  已核實 (VERIFIED)   — official source succeeded, date correct, fields
                         complete, calculation checks passed. Participates
                         in risk scoring.
  待核實 (PENDING)     — not yet updated, incomplete, or source unreachable.
                         Does NOT participate in formal scoring.
  資料矛盾 (CONFLICTED) — values/dates inconsistent or a cross-check
                         calculation doesn't match. Analysis for that field
                         stops.

Key rule from the spec, worth repeating here because it's easy to get
wrong: HTTP 200 only means the request succeeded, NOT that the data is
verified. An empty array, an HTML error page, or yesterday's data served
again under today's URL must never be marked VERIFIED.
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, List, Optional

VERIFIED = "VERIFIED"
PENDING = "PENDING"
CONFLICTED = "CONFLICTED"


@dataclass
class QualityRecord:
    """One data-quality log entry, matching the spec's JSON shape."""
    source: str                      # e.g. "TWSE", "TAIFEX", "CBC", "FRED"
    endpoint: str                    # e.g. "/exchangeReport/MI_MARGN"
    data_type: str                   # e.g. "margin_balance"
    verification_status: str         # VERIFIED / PENDING / CONFLICTED
    data_date: Optional[str] = None  # the trading/data day this value is FOR
    fetched_at: str = field(default_factory=lambda: datetime.now().astimezone().isoformat())
    market: Optional[str] = None
    raw_value: Any = None
    normalized_value: Any = None
    unit: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class DataQualityLog:
    """Accumulates QualityRecords for one pipeline run, then serializes."""

    def __init__(self):
        self._records: List[QualityRecord] = []

    def add(self, record: QualityRecord) -> QualityRecord:
        self._records.append(record)
        return record

    def coverage(self, weights: dict) -> float:
        """
        Sum of weights for data_types that are currently VERIFIED, as a
        fraction of total weight — the spec's `Coverage = Σ Valid(Wᵢ)`.
        Only the LATEST record per data_type counts (a run can log more
        than one check against the same field).
        """
        latest_status = {}
        for r in self._records:
            latest_status[r.data_type] = r.verification_status
        valid_weight = sum(w for dtype, w in weights.items() if latest_status.get(dtype) == VERIFIED)
        total_weight = sum(weights.values())
        return (valid_weight / total_weight) if total_weight else 0.0

    def as_list(self) -> List[dict]:
        return [r.to_dict() for r in self._records]


def check_http_response(resp, min_content_length: int = 1) -> Optional[str]:
    """
    Rule A (HTTP 與回應格式). Returns an error message string if the
    response fails the basic sanity check, else None (= passes this check;
    callers still need field/date/value checks before calling it VERIFIED).
    """
    if resp is None:
        return "no response (request failed before completing)"
    if resp.status_code != 200:
        return f"HTTP {resp.status_code}"
    if not resp.content or len(resp.content) < min_content_length:
        return "empty response body"
    return None


def check_non_negative(value: Optional[float], name: str) -> Optional[str]:
    """Rule D (數值合理性) — most count/amount fields must not be negative."""
    if value is None:
        return None  # missing is a separate PENDING concern, not a conflict
    if value < 0:
        return f"{name} is negative ({value})"
    return None


def check_positive(value: Optional[float], name: str) -> Optional[str]:
    """Rule D — rates and prices must be strictly positive."""
    if value is None:
        return None
    if value <= 0:
        return f"{name} must be > 0, got {value}"
    return None


def check_day_over_day_change(today: Optional[float], prev: Optional[float],
                               warn_pct: float = 10.0, reject_pct: float = 20.0) -> Optional[str]:
    """
    Rule D's variance-anomaly check: single-day change beyond `warn_pct`
    of the prior value is flagged for re-check; beyond `reject_pct` demands
    re-fetch and cross-validation. This function only classifies the
    severity — it never deletes or overrides a genuinely large market move,
    it just says how loudly to flag it.

    Returns None (no concern), "WARN: ..." or "REJECT: ..." (a message
    string — callers decide what to do; "REJECT" should usually map to
    PENDING/CONFLICTED rather than silently accepted as VERIFIED).
    """
    if today is None or prev is None or prev == 0:
        return None
    pct_change = abs((today - prev) / prev) * 100
    if pct_change > reject_pct:
        return f"REJECT: day-over-day change {pct_change:.1f}% exceeds {reject_pct}% — re-fetch and cross-check"
    if pct_change > warn_pct:
        return f"WARN: day-over-day change {pct_change:.1f}% exceeds {warn_pct}%"
    return None


def check_cross_field(computed: Optional[float], official: Optional[float],
                       tolerance_pct: float = 0.5, name: str = "value") -> Optional[str]:
    """
    Rule E (跨欄位計算驗證) — e.g. NetBuy = Buy - Sell computed from raw
    fields should match an official "net" field the source also publishes,
    within a small tolerance (rounding). A mismatch beyond tolerance means
    the field mapping or source itself is wrong — mark CONFLICTED, don't
    just average the two.
    """
    if computed is None or official is None:
        return None
    if official == 0:
        return None if computed == 0 else f"{name}: computed={computed} but official=0"
    pct_diff = abs((computed - official) / official) * 100
    if pct_diff > tolerance_pct:
        return f"{name}: computed={computed} vs official={official} (diff {pct_diff:.2f}% > {tolerance_pct}%)"
    return None
