#!/usr/bin/env python3
"""
Risk Engine — 台股市場風險評分 (Phase 2, per KD_Stock_Monitor_市場風險監控規格.docx 第二章)

Five weighted facets (0-100 each), combined into one 0-100 RiskScore:
    融資風險 30% + 法人風險 25% + 外資期貨風險 20% + 匯率風險 15% + 權值股風險 10%

Every threshold/bucket table below is explicitly labeled as either:
  (a) taken verbatim from the spec, or
  (b) an engineering default invented here because the spec gave a
      formula/weight but NO scoring table for that sub-item — the spec
      itself repeatedly says these are "初始規則模型，須以歷史資料回測校準"
      (initial rules pending backtest calibration), so an undocumented
      default is filled in the same spirit as signal_confluence.py's own
      graduated scales, never silently passed off as spec-derived.

Coverage rule (spec 第二章-6): a facet/sub-item with missing data is NEVER
scored as 0 — it's excluded, and the final RiskScore is renormalized over
only the facets that could be computed:
    RiskScore = Σ Valid(Wᵢ·Sᵢ) / Σ Valid(Wᵢ)
with Coverage = Σ Valid(Wᵢ) reported alongside so "100% / 正式分數" is never
confused with "83% / 暫定分數" (<80% coverage: no score at all, per spec).
"""

from typing import Dict, List, Optional, Tuple

FACET_WEIGHTS = {
    "margin": 0.30,
    "institutional": 0.25,
    "futures": 0.20,
    "fx": 0.15,
    "leaders": 0.10,
}

RISK_LEVEL_BANDS = [
    (20, "低風險", "市場結構相對穩定"),
    (40, "正常觀察", "可能有局部賣壓"),
    (60, "風險升高", "籌碼開始惡化"),
    (80, "高度警戒", "多項風險可能共振"),
    (100, "極端風險", "可能出現系統性賣壓"),
]


def _risk_level(score: float) -> Tuple[str, str]:
    for upper, label, desc in RISK_LEVEL_BANDS:
        if score <= upper:
            return label, desc
    return RISK_LEVEL_BANDS[-1][1], RISK_LEVEL_BANDS[-1][2]


def _window(history: List[Dict], key: str, days: int) -> Optional[List[float]]:
    """
    Same invariant as signal_confluence.py's _window(): the exact most
    recent `days` history entries (today inclusive) for `key`, or None if
    there are fewer than `days` entries OR any one of them is missing the
    key — never silently reaches further back to compensate for a gap.
    """
    if len(history) < days:
        return None
    window = history[-days:]
    vals = [h.get(key) for h in window]
    if any(v is None for v in vals):
        return None
    return vals


def _pct_change(history: List[Dict], key: str, days: int) -> Optional[float]:
    """100 * (today - N_days_ago) / |N_days_ago value|, or None if unavailable."""
    window = _window(history, key, days + 1)
    if window is None:
        return None
    start, end = window[0], window[-1]
    if start == 0:
        return None
    return (end - start) / abs(start) * 100


def _clamp(score: float) -> float:
    return max(0.0, min(100.0, score))


def _lerp(value: float, points: List[Tuple[float, float]]) -> float:
    """Piecewise-linear interpolation over ascending (value, score) control
    points, clamped outside the range — same technique as
    signal_confluence.py's _graduated(), used here only for the facets the
    spec gave no discrete bucket table for (clearly marked at each call site)."""
    if value <= points[0][0]:
        return points[0][1]
    if value >= points[-1][0]:
        return points[-1][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= value <= x1:
            return y0 + (value - x0) * (y1 - y0) / (x1 - x0)
    return points[-1][1]


# ── Facet 1: 融資風險 (30%) ───────────────────────────────────────────────

def _score_margin_5d_change(pct: float) -> float:
    """Spec table verbatim (5日融資變化 -> 分數). Deliberately U-shaped: both
    a fast build-up and a fast unwind score as elevated risk."""
    if pct >= 2:
        return 65
    if pct >= 0:
        return 45
    if pct >= -1:
        return 25
    if pct >= -2:
        return 40
    if pct >= -4:
        return 70
    return 90


def _score_margin_divergence(taiex_pct: float, margin_pct: float) -> float:
    """
    Spec table verbatim (大盤 x 融資 -> 分數). "緩慢"/"快速" aren't numerically
    defined in the spec — (b) engineering default: reusing the adjacent
    table's own 0~2% vs >2% split (the same boundary the 5-day-change table
    uses between its "mild" and "fast" decline buckets) so the two tables
    stay internally consistent rather than inventing an unrelated cutoff.
    """
    taiex_up = taiex_pct >= 0
    if taiex_up:
        return 15 if margin_pct <= 0 else 30
    # taiex down
    if margin_pct > 0:
        return 90  # 下跌、融資反而增加
    if margin_pct >= -2:
        return 45  # 緩慢下降
    return 85  # 快速下降 (>2%跌幅)


def compute_margin_facet(history: List[Dict]) -> Dict:
    """
    融資風險 = 0.4·A(餘額變化) + 0.35·B(去槓桿速度) + 0.25·C(指數融資背離)

    (b) The spec defines A via M5/M20 and B via an identically-shaped D5
    formula (D5 = M5*100) with only ONE scoring table given, directly under
    B's heading. Rather than invent a second, unspecified table for A, A is
    scored through the same verbatim table as B, applied to M5 — meaning A
    and B share one input by the spec's own formulas; this is not a bug
    introduced here, it's what the given formulas literally produce. M20 is
    reported as context but isn't separately scored (no table exists for it).
    """
    m5 = _pct_change(history, "margin_balance_amount", 5)
    m20 = _pct_change(history, "margin_balance_amount", 20)
    taiex5 = _pct_change(history, "taiex", 5)

    if m5 is None:
        return {"available": False, "reason": "insufficient margin_balance_amount history (need 6 days)"}

    score_a = _score_margin_5d_change(m5)
    score_b = score_a  # see docstring — same input per spec's own formulas
    score_c = _score_margin_divergence(taiex5, m5) if taiex5 is not None else None

    if score_c is None:
        # C unavailable: renormalize over A+B only (both currently identical,
        # so this reduces to just A — still a valid partial score, not a 0).
        facet_score = 0.4 * score_a + 0.35 * score_b
        facet_score = facet_score / 0.75
    else:
        facet_score = 0.4 * score_a + 0.35 * score_b + 0.25 * score_c

    return {
        "available": True, "score": round(_clamp(facet_score), 1),
        "inputs": {"m5_pct": round(m5, 2), "m20_pct": round(m20, 2) if m20 is not None else None,
                   "taiex_5d_pct": round(taiex5, 2) if taiex5 is not None else None},
    }


# ── Facet 2: 法人風險 (25%) ───────────────────────────────────────────────

def _score_foreign_ratio(ratio_pct: float) -> float:
    """Spec table verbatim (外資N日淨買賣超/N日成交金額 -> 分數)."""
    if ratio_pct > 2:
        return 5
    if ratio_pct > 1:
        return 20
    if ratio_pct > 0:
        return 35
    if ratio_pct > -1:
        return 55
    if ratio_pct > -2:
        return 75
    return 95


def compute_institutional_facet(history: List[Dict]) -> Dict:
    """
    法人風險 = 0.5·A(外資5日/成交金額) + 0.3·B(外資20日/成交金額) + 0.2·C(投信+自營商方向)

    (b) C's scoring rule ("是否同步賣超") has no numeric table in the spec —
    engineering default: both trust+dealer net-selling over 5 days -> 90,
    both net-buying -> 10, mixed/either unavailable -> 50 (neutral).
    """
    f5_window = _window(history, "foreign_net", 5)
    turnover5_window = _window(history, "market_turnover_amount", 5)
    f20_window = _window(history, "foreign_net", 20)
    turnover20_window = _window(history, "market_turnover_amount", 20)

    if f5_window is None or turnover5_window is None:
        return {"available": False, "reason": "insufficient foreign_net/market_turnover_amount history (need 5 days)"}

    f5 = sum(f5_window)
    turnover5 = sum(turnover5_window)
    if turnover5 == 0:
        return {"available": False, "reason": "zero market turnover in window"}
    ratio5 = f5 / turnover5 * 100
    score_a = _score_foreign_ratio(ratio5)

    score_b = None
    ratio20 = None
    if f20_window is not None and turnover20_window is not None:
        f20 = sum(f20_window)
        turnover20 = sum(turnover20_window)
        if turnover20 != 0:
            ratio20 = f20 / turnover20 * 100
            score_b = _score_foreign_ratio(ratio20)

    trust5 = _window(history, "trust_net", 5)
    dealer_self5 = _window(history, "dealer_self_net", 5)
    dealer_hedge5 = _window(history, "dealer_hedge_net", 5)
    score_c = None
    if trust5 is not None and dealer_self5 is not None and dealer_hedge5 is not None:
        trust_sum = sum(trust5)
        dealer_sum = sum(dealer_self5) + sum(dealer_hedge5)
        if trust_sum < 0 and dealer_sum < 0:
            score_c = 90
        elif trust_sum > 0 and dealer_sum > 0:
            score_c = 10
        else:
            score_c = 50

    weights = {"a": 0.5, "b": 0.3, "c": 0.2}
    parts = {"a": score_a, "b": score_b, "c": score_c}
    valid_weight = sum(w for k, w in weights.items() if parts[k] is not None)
    if valid_weight == 0:
        return {"available": False, "reason": "no scoreable sub-item"}
    facet_score = sum(weights[k] * parts[k] for k in parts if parts[k] is not None) / valid_weight

    return {
        "available": True, "score": round(_clamp(facet_score), 1),
        "inputs": {"foreign_ratio5_pct": round(ratio5, 3),
                   "foreign_ratio20_pct": round(ratio20, 3) if ratio20 is not None else None},
    }


# ── Facet 3: 外資期貨風險 (20%) ────────────────────────────────────────────

def _score_short_ratio(ratio_pct: float) -> float:
    """Spec table verbatim (淨空單占未平倉部位比例 -> 分數)."""
    if ratio_pct < 0:
        return 10
    if ratio_pct < 10:
        return 30
    if ratio_pct < 20:
        return 50
    if ratio_pct < 30:
        return 70
    if ratio_pct < 40:
        return 85
    return 95


def spot_futures_divergence(spot_net: Optional[float], futures_delta5: Optional[float]) -> Optional[Dict]:
    """
    外資現貨與期貨背離分析 (spec 第六章-1 / 建議新增功能-1) — a standalone
    read, not just a futures-facet input: classifies today's spot flow
    direction against the 5-day change in futures net-short position.
    """
    if spot_net is None or futures_delta5 is None:
        return None
    spot_sell = spot_net < 0
    short_increasing = futures_delta5 > 0  # delta of (Short-Long); positive = more net short
    if spot_sell and short_increasing:
        return {"pattern": "賣超_空單增加", "reading": "撤退風險提高"}
    if spot_sell and not short_increasing:
        return {"pattern": "賣超_空單減少", "reading": "可能有期貨空單回補"}
    if not spot_sell and short_increasing:
        return {"pattern": "買超_空單增加", "reading": "現貨與期貨方向背離"}
    return {"pattern": "買超_空單減少", "reading": "籌碼方向相對有利"}


def compute_futures_facet(history: List[Dict]) -> Dict:
    """
    外資期貨風險 = 0.4·A(淨空單占未平倉比例) + 0.4·B(5日淨空單變化) + 0.2·C(現貨期貨方向)

    NetShort (spec's sign convention) = ShortOI - LongOI; TAIFEX's own
    OpenInterest(Net) field is Long - Short, so NetShort = -OpenInterest(Net)
    (see fetcher.fetch_tx_foreign_futures_official()'s long_oi/short_oi).
    """
    long_oi = _window(history, "tx_long_oi", 1)
    short_oi = _window(history, "tx_short_oi", 1)
    if long_oi is None or short_oi is None:
        return {"available": False, "reason": "insufficient tx_long_oi/tx_short_oi history"}
    long_oi, short_oi = long_oi[0], short_oi[0]
    if long_oi + short_oi == 0:
        return {"available": False, "reason": "LongOI+ShortOI = 0"}
    short_ratio = (short_oi - long_oi) / (long_oi + short_oi) * 100
    score_a = _score_short_ratio(short_ratio)

    ns_window = _window(history, "foreign_futures_net_taifex", 6)  # NS = Long-Short here; delta sign flips below
    score_b = None
    delta_ns5 = None
    if ns_window is not None:
        # history field is Long-Short; spec's NetShort is Short-Long, so negate.
        net_short_series = [-v for v in ns_window]
        delta_ns5 = net_short_series[-1] - net_short_series[0]
        # (b) No scoring table given for ΔNS5 itself — engineering default:
        # graduated scale anchored loosely to the existing
        # FOREIGN_FUTURES_NET_SHORT_THRESHOLD-style magnitudes already used
        # in signal_confluence.py (tens of thousands of contracts = material).
        score_b = _lerp(delta_ns5, [(-20000, 10), (0, 40), (10000, 70), (30000, 100)])

    spot_net = _window(history, "foreign_net", 1)
    divergence = spot_futures_divergence(spot_net[0] if spot_net else None, delta_ns5)
    score_c = {"撤退風險提高": 90, "現貨與期貨方向背離": 60,
               "可能有期貨空單回補": 35, "籌碼方向相對有利": 15}.get(
        divergence["reading"] if divergence else None)

    weights = {"a": 0.4, "b": 0.4, "c": 0.2}
    parts = {"a": score_a, "b": score_b, "c": score_c}
    valid_weight = sum(w for k, w in weights.items() if parts[k] is not None)
    facet_score = sum(weights[k] * parts[k] for k in parts if parts[k] is not None) / valid_weight

    return {
        "available": True, "score": round(_clamp(facet_score), 1),
        "inputs": {"short_ratio_pct": round(short_ratio, 2),
                   "delta_net_short_5d": round(delta_ns5) if delta_ns5 is not None else None},
        "divergence": divergence,
    }


# ── Facet 4: 匯率風險 (15%) ───────────────────────────────────────────────

def compute_fx_facet(history: List[Dict]) -> Dict:
    """
    匯率風險 = 0.5·A(USD/TWD 5日) + 0.3·B(USD/TWD 20日) + 0.2·C(美元指數5日)

    Uses usdtwd_cbc (央行銀行間收盤匯率, the spec's required definition) —
    NOT the yfinance usdtwd market quote. USD/TWD rising = TWD depreciation.
    """
    fx5 = _pct_change(history, "usdtwd_cbc", 5)
    if fx5 is None:
        return {"available": False, "reason": "insufficient usdtwd_cbc history (need 6 days)"}
    score_a = _score_fx5_depreciation(fx5)

    fx20 = _pct_change(history, "usdtwd_cbc", 20)
    score_b = _score_fx5_depreciation(fx20) if fx20 is not None else None

    dxy5 = _pct_change(history, "dxy", 5)
    score_c = _score_fx5_depreciation(dxy5) if dxy5 is not None else None  # same direction logic: DXY up = USD strength

    weights = {"a": 0.5, "b": 0.3, "c": 0.2}
    parts = {"a": score_a, "b": score_b, "c": score_c}
    valid_weight = sum(w for k, w in weights.items() if parts[k] is not None)
    facet_score = sum(weights[k] * parts[k] for k in parts if parts[k] is not None) / valid_weight

    return {
        "available": True, "score": round(_clamp(facet_score), 1),
        "inputs": {"usdtwd_5d_pct": round(fx5, 3), "usdtwd_20d_pct": round(fx20, 3) if fx20 is not None else None,
                   "dxy_5d_pct": round(dxy5, 3) if dxy5 is not None else None},
    }


def _score_fx5_depreciation(pct: float) -> float:
    """Spec table verbatim (5日新台幣貶值幅度 -> 分數); applied with the same
    breakpoints to the 20-day window and to DXY (b: spec says give DXY/20-day
    "各自適當門檻" without specifying them — reusing this table is the
    documented default pending calibration, not a verbatim spec table for
    those two)."""
    if pct < 0:
        return 10
    if pct <= 0.5:
        return 25
    if pct <= 1.0:
        return 50
    if pct <= 1.5:
        return 75
    return 95


# ── Facet 5: 權值股風險 (10%) ─────────────────────────────────────────────

def _return5_from_closes(closes: List[float]) -> Optional[float]:
    if len(closes) < 6 or closes[-6] == 0:
        return None
    return (closes[-1] - closes[-6]) / closes[-6] * 100


def compute_leaders_facet(closes_2330: Optional[List[float]], closes_0050: Optional[List[float]],
                           foreign_net_5d_2330: Optional[float]) -> Dict:
    """
    權值股風險 = 0.3·A(2330 五日報酬) + 0.4·B(2330 外資5日累計買賣超) + 0.3·C(0050 五日報酬)

    (b) The spec gives Return5's FORMULA for A/C and foreign_net_5d for B,
    but no scoring table for any of the three — engineering defaults below,
    pending calibration like every other facet.
    """
    r5_2330 = _return5_from_closes(closes_2330) if closes_2330 else None
    r5_0050 = _return5_from_closes(closes_0050) if closes_0050 else None

    # More negative 5-day return = higher risk; symmetric, mild upside relief.
    return_scale = [(-10, 100), (-5, 80), (-2, 55), (0, 35), (3, 15), (6, 0)]
    score_a = _lerp(r5_2330, return_scale) if r5_2330 is not None else None
    score_c = _lerp(r5_0050, return_scale) if r5_0050 is not None else None

    score_b = None
    if foreign_net_5d_2330 is not None:
        lots_5d = foreign_net_5d_2330 / 1000  # shares -> 張
        # Judgment-call scale (no reference threshold given for TSMC foreign
        # flow magnitude) — ±20,000張/5日 as "moderate", ±50,000張 as "heavy".
        score_b = _lerp(lots_5d, [(-50000, 95), (-20000, 70), (0, 45), (20000, 20), (50000, 5)])

    weights = {"a": 0.3, "b": 0.4, "c": 0.3}
    parts = {"a": score_a, "b": score_b, "c": score_c}
    valid_weight = sum(w for k, w in weights.items() if parts[k] is not None)
    if valid_weight == 0:
        return {"available": False, "reason": "no price/flow data available"}
    facet_score = sum(weights[k] * parts[k] for k in parts if parts[k] is not None) / valid_weight

    return {
        "available": True, "score": round(_clamp(facet_score), 1),
        "inputs": {"tsmc_return5_pct": round(r5_2330, 2) if r5_2330 is not None else None,
                   "etf0050_return5_pct": round(r5_0050, 2) if r5_0050 is not None else None,
                   "tsmc_foreign_net_5d_lots": round(foreign_net_5d_2330 / 1000) if foreign_net_5d_2330 is not None else None},
    }


# ── Combined score ───────────────────────────────────────────────────────

def compute_risk_score(history: List[Dict], closes_2330: Optional[List[float]] = None,
                        closes_0050: Optional[List[float]] = None,
                        foreign_net_5d_2330: Optional[float] = None) -> Dict:
    """
    Top-level entry point: computes all 5 facets and combines them per the
    spec's coverage rule. Never fabricates a facet score from missing data —
    an unavailable facet is dropped from both the numerator and the
    denominator, and `coverage_pct` / `status` tell the caller whether the
    result is a 正式風險分數 (100%), 暫定分數 (80-99%), or no score at all
    (<80%, per spec — `available` is False in that case).
    """
    facets = {
        "margin": compute_margin_facet(history),
        "institutional": compute_institutional_facet(history),
        "futures": compute_futures_facet(history),
        "fx": compute_fx_facet(history),
        "leaders": compute_leaders_facet(closes_2330, closes_0050, foreign_net_5d_2330),
    }

    valid_weight = sum(FACET_WEIGHTS[k] for k, f in facets.items() if f.get("available"))
    coverage_pct = round(valid_weight * 100, 1)

    result = {"facets": facets, "coverage_pct": coverage_pct}

    if coverage_pct < 80:
        result["available"] = False
        result["status"] = "coverage_too_low"
        return result

    weighted_sum = sum(FACET_WEIGHTS[k] * f["score"] for k, f in facets.items() if f.get("available"))
    score = weighted_sum / valid_weight
    level, level_desc = _risk_level(score)

    result.update({
        "available": True,
        "score": round(score, 1),
        "status": "formal" if coverage_pct >= 99.9 else "provisional",
        "risk_level": level,
        "risk_level_desc": level_desc,
    })
    return result


# ── 融資下降速度與指數跌幅比較 (spec 第六章-2 / 建議新增功能-2) ──────────────

def margin_deleverage_vs_index(history: List[Dict]) -> Optional[Dict]:
    """
    Compares the 5-day TAIEX move against the 5-day margin-balance move to
    distinguish ordinary correction / fast deleveraging / leverage-up-into-
    a-selloff — a standalone read, same inputs as the margin facet's C
    component but reported on its own per the spec's "建議新增功能".
    """
    taiex5 = _pct_change(history, "taiex", 5)
    margin5 = _pct_change(history, "margin_balance_amount", 5)
    if taiex5 is None or margin5 is None:
        return None
    if taiex5 >= 0:
        pattern = "大盤上漲"
    elif margin5 > 0:
        pattern = "大盤下跌_融資逆勢增加"
    elif margin5 >= taiex5:
        # margin fell less (in % terms) than the index — deleveraging lagging the selloff
        pattern = "大盤下跌_融資緩慢去槓桿"
    else:
        pattern = "大盤下跌_融資快速去槓桿"
    return {"taiex_5d_pct": round(taiex5, 2), "margin_5d_pct": round(margin5, 2), "pattern": pattern}
