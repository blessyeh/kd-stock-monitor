#!/usr/bin/env python3
"""
Signal Confluence — 大盤轉折訊號共振模型

Implements the user-specified "top structure / hedge-trigger" and "bottom
turning point / add-position" confluence framework: no single macro or chip
indicator is trusted in isolation, multiple independent signals have to agree
before the model calls a turning point.

Data-availability note: 外資台指期未平倉淨部位 and 選擇權 Put/Call Ratio are
fetched via FinMind (see fetcher.py's fetch_tw_chip_indicators()), so all
conditions below can now be fully evaluated. Older history entries recorded
before that field was added simply won't have foreign_futures_net /
put_call_ratio — the window helpers below report "insufficient data"
(status=None) until enough post-upgrade history accumulates, rather than
crashing or silently mis-scoring. The same applies to sox/ndx (added
alongside the T5 condition below).

Index choice note (T5): TWSE's weighted index is effectively a tech/
semiconductor-heavy index (TSMC + supply chain dominate its weighting), so
SOX and NDX are used as the "source pricing" leading indicators instead of
the Dow — the Dow's blue-chip/industrial composition has little correlation
with TW corporate earnings or capital flows.

This module only reads the persisted daily history (data/macro_history.json)
plus the module producing it — it doesn't fetch anything itself.

Date-alignment note (fixed 2026-08-09 — read this before adding a new
condition): every condition below reads `history` — a date-ascending list of
daily snapshots, one entry per calendar/trading day — via `_window()` /
`_lookback()`, never via a hand-rolled list comprehension that drops None
values. The earlier version used a helper that stripped out any day missing
a given field before taking the last N *values*, e.g. for a field with one
gap:
    8/1 -100, 8/2 None, 8/3 -200, 8/4 -300
    -> compacted series: [-100, -200, -300]
A "last 3 days" or "5-day change" check against that compacted series
silently compares 8/1 vs 8/4 as if they were 3 trading days apart, when
they're actually 4 — the missing 8/2 doesn't shrink the window, it just
disappears without leaving a gap. `_window()` instead requires every day in
the exact N-day calendar window to have a value; if even one is missing, the
whole window reports unavailable (None) rather than silently reaching
further back to compensate. This makes conditions unavailable slightly more
often (a single missing field can block a whole window instead of one
window it's actually part of), which is the intended, safer trade-off — the
alternative is looking calibrated while quietly measuring the wrong period.
"""

from typing import Dict, List, Optional, Tuple

# ── Tunable thresholds (documented, not hidden magic numbers) ───────────────
DXY_BREAKOUT_LOOKBACK_DAYS = 20      # "前高" = highest DXY close in the past N days
US10Y_FAST_RISE_LOOKBACK_DAYS = 5    # "快速攀升" window
US10Y_FAST_RISE_THRESHOLD = 0.15     # percentage points over that window
TWD_DEPRECIATION_LOOKBACK_DAYS = 5
TWD_DEPRECIATION_THRESHOLD = 0.3     # USD/TWD rising by this much = meaningful depreciation
TWD_ROUND_NUMBER_STEP = 1.0          # "整數關卡" step size (NT$1) — see T2 for why this replaced int(x) comparison
FOREIGN_SELL_STREAK_DAYS = 3         # "連續賣超" — consecutive days of net-sell
MARGIN_NOT_RETREATING_LOOKBACK_DAYS = 5
VIX_PEAK_LOOKBACK_DAYS = 10
VIX_PEAK_THRESHOLD = 30.0
VIX_ROLLOVER_RATIO = 0.85            # "見頂回落" = current VIX <= 85% of the recent peak
MARGIN_CAPITULATION_LOOKBACK_DAYS = 5
MARGIN_CAPITULATION_DROP_NTB = 30.0  # single-day drop (億元) counted as "斷頭式大減"
FOREIGN_FUTURES_NET_SHORT_THRESHOLD = 30000  # 口, per the user's own "3萬至4萬口以上" spec
PUT_CALL_RATIO_LOW_THRESHOLD = 100.0          # "跌破100%" = call side crowded = complacent
FUTURES_COVERING_LOOKBACK_DAYS = 5
FUTURES_COVERING_THRESHOLD = 5000    # 口 — net position moving less-short by at least this much
TECH_BREAKDOWN_LOOKBACK_DAYS = 20    # "重要支撐" = lowest SOX/NDX close in the past N days
FOREIGN_RECENT_AVG_WINDOW = 5        # "近期均值" window used by B3's flow-reversal check

# ── Graduated 0-100 scales (roadmap item 1) ──────────────────────────────────
# Each condition below used to be a hard AND/OR boolean — e.g. a 0.14pp vs.
# 0.15pp US10Y move is barely a different market state but used to flip the
# whole condition from 0 to 1 with nothing in between. Every condition now
# ALSO computes a 0-100 `score` via piecewise-linear interpolation over these
# control points (ascending by value), so two readings just below and just
# above a legacy threshold score nearly identically instead of jumping. The
# original boolean `status` is unchanged and still drives `triggered_count` —
# `score` is purely additive, for ranking "how strong" a condition currently
# reads. Each scale's control points are anchored so the *value* at the
# original hard threshold lands around 60-70 (a clean pass, not yet maxed
# out) — see _graduated()'s docstring for why interpolation was chosen over
# discrete buckets.
US10Y_FAST_RISE_SCALE: List[Tuple[float, float]] = [
    (-0.10, 0), (0.0, 10), (0.05, 30), (0.10, 50), (0.15, 70), (0.25, 100),
]
DXY_BREAKOUT_PCT_SCALE: List[Tuple[float, float]] = [  # % today is above/below the prior high
    (-2.0, 0), (-0.5, 30), (0.0, 60), (0.5, 85), (1.0, 100),
]
TWD_DEPRECIATION_SCALE: List[Tuple[float, float]] = [  # 5-day USD/TWD change
    (-0.3, 0), (0.0, 20), (0.15, 40), (0.3, 70), (0.5, 90), (0.8, 100),
]
FOREIGN_FLOW_AVG_SELL_SCALE: List[Tuple[float, float]] = [  # avg 億元/day, negative = selling
    (20, 0), (0, 20), (-20, 45), (-50, 75), (-100, 100),
]
FUTURES_NET_SHORT_SCALE: List[Tuple[float, float]] = [  # 口, more negative = heavier short
    (0, 0), (-10000, 20), (-20000, 45), (-30000, 70), (-45000, 90), (-60000, 100),
]
MARGIN_STUBBORN_SCALE: List[Tuple[float, float]] = [  # 億元 change, positive = still rising
    (-30, 0), (0, 50), (30, 80), (60, 100),
]
PUT_CALL_RATIO_COMPLACENCY_SCALE: List[Tuple[float, float]] = [  # lower ratio = more complacent
    (70, 100), (85, 75), (100, 50), (115, 25), (130, 0),
]
TECH_BREAKDOWN_PCT_SCALE: List[Tuple[float, float]] = [  # % below support, negative = still above
    (-2.0, 0), (-0.5, 25), (0.0, 55), (1.0, 80), (2.5, 100),
]
VIX_PEAK_SCALE: List[Tuple[float, float]] = [
    (20, 0), (30, 40), (40, 70), (55, 90), (70, 100),
]
VIX_ROLLOVER_RATIO_SCALE: List[Tuple[float, float]] = [  # today/peak, lower = more rolled over
    (0.5, 100), (0.7, 85), (0.85, 60), (1.0, 20), (1.2, 0),
]
MARGIN_CAPITULATION_SCALE: List[Tuple[float, float]] = [  # 億元 single-day drop, negative = bigger
    (10, 0), (0, 15), (-15, 40), (-30, 70), (-50, 90), (-80, 100),
]
# B3 "Bottom Reversal Score" component scales (see bottom_reversal_score()):
FX_STABILIZATION_SCALE: List[Tuple[float, float]] = [  # 5-day USD/TWD change, negative = appreciating
    (-0.5, 100), (-0.15, 75), (0.0, 55), (0.15, 30), (0.3, 10), (0.5, 0),
]
FOREIGN_REVERSAL_DELTA_SCALE: List[Tuple[float, float]] = [  # today's flow minus recent avg, 億元
    (-20, 0), (0, 20), (20, 50), (50, 80), (90, 100),
]
FUTURES_COVERING_AMOUNT_SCALE: List[Tuple[float, float]] = [  # 口, net position moving less-short
    (-5000, 0), (0, 15), (5000, 55), (15000, 80), (30000, 100),
]
BOTTOM_REVERSAL_WEIGHTS = {"fx_stabilization": 30, "foreign_flow_reversal": 35, "futures_covering": 35}


def _graduated(value: Optional[float], points: List[Tuple[float, float]]) -> Optional[float]:
    """
    Piecewise-linear interpolation of `value` over ascending (value, score)
    control points, clamped to the first/last score outside the range.
    Returns None if `value` is None.

    Deliberately linear rather than discrete buckets: a step function just
    moves the cliff to different value, it doesn't remove it. Interpolating
    means a value 0.01 either side of a bucket boundary scores 0.01-worth
    apart, not 20 points apart.
    """
    if value is None:
        return None
    if value <= points[0][0]:
        return float(points[0][1])
    if value >= points[-1][0]:
        return float(points[-1][1])
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= value <= x1:
            if x1 == x0:
                return float(y0)
            return float(y0 + (y1 - y0) * (value - x0) / (x1 - x0))
    return float(points[-1][1])  # unreachable given the bounds checks above


def _avg(*scores: Optional[float]) -> Optional[float]:
    """Average of the non-None scores, or None if all are None."""
    vals = [s for s in scores if s is not None]
    return sum(vals) / len(vals) if vals else None


def _weighted(*pairs: Tuple[Optional[float], float]) -> Optional[float]:
    """Weighted average of (score, weight) pairs, renormalized over whichever
    scores are available (None entries dropped from both numerator and the
    weight total), or None if none are available."""
    available = [(s, w) for s, w in pairs if s is not None]
    total_weight = sum(w for _, w in available)
    if not available or total_weight == 0:
        return None
    return sum(s * w for s, w in available) / total_weight


def _window(history: List[Dict], key: str, days: int) -> Optional[List[float]]:
    """
    Values of `key` for the most recent `days` calendar-history entries
    (today inclusive), in chronological order — or None if fewer than
    `days` entries exist yet, OR any single entry inside that exact window
    is missing the key. See the module docstring for why a gap invalidates
    the whole window instead of being skipped over.
    """
    if len(history) < days:
        return None
    window = history[-days:]
    vals = [h.get(key) for h in window]
    if any(v is None for v in vals):
        return None
    return vals


def _lookback(history: List[Dict], key: str, days_ago: int) -> Optional[float]:
    """Value of `key` exactly `days_ago` history-entries back from today
    (0 = today itself), or None if that day doesn't exist or lacks the key."""
    idx = -(days_ago + 1)
    if len(history) < -idx:
        return None
    return history[idx].get(key)


def _condition(cid: str, label: str, status: Optional[bool], completeness: str, detail: str,
                score: Optional[float] = None) -> Dict:
    # Defensive cast: every condition above computes `status` via comparisons
    # (>, >=, <, and/or) on values from history. main.py's _to_native() should
    # already keep numpy types out of that history, but this is the single
    # choke point all 8 conditions pass through — cheap insurance against a
    # numpy.bool_ (which json.dump() can't serialize) slipping into the
    # persisted summary from here or any future condition added later.
    if status is not None:
        status = bool(status)
    if score is not None:
        score = round(float(score), 1)
    return {"id": cid, "label": label, "status": status, "completeness": completeness, "detail": detail,
            "score": score}


def _top_conditions(history: List[Dict]) -> List[Dict]:
    conditions = []

    # T1. 宏觀資金抽離: DXY 突破前高 AND 美債10Y快速攀升 — 完整可驗證
    dxy_window = _window(history, "dxy", DXY_BREAKOUT_LOOKBACK_DAYS + 1)
    us10y_window = _window(history, "us10y", US10Y_FAST_RISE_LOOKBACK_DAYS + 1)
    if dxy_window is not None and us10y_window is not None:
        dxy_today = dxy_window[-1]
        dxy_prior_high = max(dxy_window[:-1])
        us10y_today = us10y_window[-1]
        us10y_change = us10y_today - us10y_window[0]
        dxy_breakout = dxy_today > dxy_prior_high
        us10y_fast_rise = us10y_change >= US10Y_FAST_RISE_THRESHOLD
        status = dxy_breakout and us10y_fast_rise
        dxy_pct = (dxy_today - dxy_prior_high) / dxy_prior_high * 100 if dxy_prior_high else None
        score = _avg(_graduated(dxy_pct, DXY_BREAKOUT_PCT_SCALE), _graduated(us10y_change, US10Y_FAST_RISE_SCALE))
        detail = (f"DXY {dxy_today:.2f} vs 近{DXY_BREAKOUT_LOOKBACK_DAYS}日高點 {dxy_prior_high:.2f}"
                  f"（{'突破' if dxy_breakout else '未突破'}）；"
                  f"美債10Y {US10Y_FAST_RISE_LOOKBACK_DAYS}日變動 {us10y_change:+.2f}pp"
                  f"（{'達標' if us10y_fast_rise else '未達'} {US10Y_FAST_RISE_THRESHOLD}pp）")
    else:
        status, detail, score = None, "歷史資料不足或期間內有缺漏，尚無法判斷", None
    conditions.append(_condition("macro_drain", "宏觀資金抽離 (DXY突破前高+美債10Y快速攀升)", status, "full", detail, score))

    # T2. 匯率表態: 新台幣連續走貶 / 貶破整數關卡 — 完整可驗證
    #
    # "貶破整數關卡" fix: the previous `int(today) > int(prior)` check isn't
    # actually a round-number crossing test — int() truncates toward zero at
    # *every* integer boundary regardless of step size, so e.g. 30.99 -> 31.01
    # (a genuine NT$31 crossing) and 29.99 -> 30.01 (also a genuine crossing)
    # both read as True, which happens to be correct here only because the
    # intended step size (NT$1) coincides with int()'s own truncation unit.
    # Made explicit via floor(value / step) so the step size is a real,
    # documented, changeable parameter (TWD_ROUND_NUMBER_STEP) instead of an
    # accidental side effect of using int().
    usdtwd_window = _window(history, "usdtwd", TWD_DEPRECIATION_LOOKBACK_DAYS + 1)
    if usdtwd_window is not None:
        today = usdtwd_window[-1]
        prior = usdtwd_window[0]
        change = today - prior
        crossed_round_number = (
            today // TWD_ROUND_NUMBER_STEP > prior // TWD_ROUND_NUMBER_STEP
        )
        status = change >= TWD_DEPRECIATION_THRESHOLD or crossed_round_number
        # Crossing a round-number level is itself a meaningful psychological
        # trigger regardless of the raw magnitude, so it floors the score
        # rather than just averaging in — mirrors the boolean OR above.
        base_score = _graduated(change, TWD_DEPRECIATION_SCALE)
        score = max(base_score, 65) if crossed_round_number and base_score is not None else base_score
        detail = (f"USD/TWD {TWD_DEPRECIATION_LOOKBACK_DAYS}日變動 {change:+.3f}"
                  f"（貶值門檻 {TWD_DEPRECIATION_THRESHOLD}）"
                  + (f"；期間貶破NT${TWD_ROUND_NUMBER_STEP:.0f}整數關卡" if crossed_round_number else ""))
    else:
        status, detail, score = None, "歷史資料不足或期間內有缺漏，尚無法判斷", None
    conditions.append(_condition("twd_depreciation", "匯率表態 (新台幣連續走貶/貶破關卡)", status, "full", detail, score))

    # T3. 外資期現貨雙空: 現貨連續賣超 + 台指期淨空單達門檻 — 完整可驗證 (FinMind)
    foreign_window = _window(history, "foreign_net", FOREIGN_SELL_STREAK_DAYS)
    futures_net_today = _lookback(history, "foreign_futures_net", 0)
    if foreign_window is not None and futures_net_today is not None:
        spot_sell_streak = all(v < 0 for v in foreign_window)
        futures_heavy_short = futures_net_today <= -FOREIGN_FUTURES_NET_SHORT_THRESHOLD
        status = spot_sell_streak and futures_heavy_short
        foreign_avg = sum(foreign_window) / len(foreign_window)
        score = _avg(_graduated(foreign_avg, FOREIGN_FLOW_AVG_SELL_SCALE),
                     _graduated(futures_net_today, FUTURES_NET_SHORT_SCALE))
        detail = (f"外資現貨連續{FOREIGN_SELL_STREAK_DAYS}日賣超："
                  f"{'是' if spot_sell_streak else '否'}（{[round(v,1) for v in foreign_window]}億元）；"
                  f"台指期淨部位 {futures_net_today:+.0f}口"
                  f"（{'達' if futures_heavy_short else '未達'} -{FOREIGN_FUTURES_NET_SHORT_THRESHOLD:.0f}口門檻）")
    else:
        status, detail, score = None, "歷史資料不足或期間內有缺漏，尚無法判斷", None
    conditions.append(_condition("foreign_dual_short", "外資期現貨雙空", status, "full", detail, score))

    # T4. 籌碼過度樂觀/散戶接刀: 外資賣超+融資不退+P/C Ratio<100% — 完整可驗證 (FinMind)
    margin_amt_window = _window(history, "margin_balance_amount", MARGIN_NOT_RETREATING_LOOKBACK_DAYS + 1)
    foreign_today = _lookback(history, "foreign_net", 0)
    pc_ratio_today = _lookback(history, "put_call_ratio", 0)
    if margin_amt_window is not None and foreign_today is not None and pc_ratio_today is not None:
        foreign_selling_today = foreign_today < 0
        margin_not_retreating = margin_amt_window[-1] >= margin_amt_window[0]
        pc_ratio_low = pc_ratio_today < PUT_CALL_RATIO_LOW_THRESHOLD
        status = foreign_selling_today and margin_not_retreating and pc_ratio_low
        margin_delta = margin_amt_window[-1] - margin_amt_window[0]
        score = _weighted(
            (_graduated(foreign_today, FOREIGN_FLOW_AVG_SELL_SCALE), 35),
            (_graduated(margin_delta, MARGIN_STUBBORN_SCALE), 30),
            (_graduated(pc_ratio_today, PUT_CALL_RATIO_COMPLACENCY_SCALE), 35),
        )
        detail = (f"今日外資{'賣超' if foreign_selling_today else '買超'}；"
                  f"融資餘額{MARGIN_NOT_RETREATING_LOOKBACK_DAYS}日"
                  f"{'未回落' if margin_not_retreating else '已回落'}"
                  f"（{margin_amt_window[-1]:.0f}億元）；"
                  f"P/C Ratio {pc_ratio_today:.1f}%"
                  f"（{'<' if pc_ratio_low else '>='} {PUT_CALL_RATIO_LOW_THRESHOLD:.0f}%門檻）")
    else:
        status, detail, score = None, "歷史資料不足或期間內有缺漏，尚無法判斷", None
    conditions.append(_condition("retail_holding_bag", "籌碼過度樂觀/散戶接刀", status, "full", detail, score))

    # T5. 科技資金退潮: 費半(SOX)或那斯達克100(NDX)跌破近期支撐 AND 美債10Y快速攀升
    # — 完整可驗證。台股加權指數本質是「科技/半導體重壓指數」（台積電及供應鏈佔絕對
    # 權重），SOX/NDX 的轉折是台股轉折的源頭定價，比道瓊等傳產指數更有預測力，因此
    # 用「跌破支撐」而非「跌幅」來定義：只要兩者之一跌破近 N 日低點，視為結構轉弱。
    us10y_window = _window(history, "us10y", US10Y_FAST_RISE_LOOKBACK_DAYS + 1)
    sox_window = _window(history, "sox", TECH_BREAKDOWN_LOOKBACK_DAYS + 1)
    ndx_window = _window(history, "ndx", TECH_BREAKDOWN_LOOKBACK_DAYS + 1)
    if us10y_window is not None and (sox_window is not None or ndx_window is not None):
        us10y_today = us10y_window[-1]
        us10y_change = us10y_today - us10y_window[0]
        us10y_fast_rise = us10y_change >= US10Y_FAST_RISE_THRESHOLD

        sox_breakdown, sox_pct = None, None
        if sox_window is not None:
            sox_today = sox_window[-1]
            sox_support = min(sox_window[:-1])
            sox_breakdown = sox_today < sox_support
            sox_pct = (sox_today - sox_support) / sox_support * 100 if sox_support else None

        ndx_breakdown, ndx_pct = None, None
        if ndx_window is not None:
            ndx_today = ndx_window[-1]
            ndx_support = min(ndx_window[:-1])
            ndx_breakdown = ndx_today < ndx_support
            ndx_pct = (ndx_today - ndx_support) / ndx_support * 100 if ndx_support else None

        tech_breakdown = bool(sox_breakdown) or bool(ndx_breakdown)
        status = tech_breakdown and us10y_fast_rise
        # Use whichever index sits further below its own support (the
        # strongest breakdown reading of the two) for the graduated score.
        pct_candidates = [p for p in (sox_pct, ndx_pct) if p is not None]
        tech_pct = min(pct_candidates) if pct_candidates else None
        score = _avg(_graduated(tech_pct, TECH_BREAKDOWN_PCT_SCALE), _graduated(us10y_change, US10Y_FAST_RISE_SCALE))
        detail_parts = []
        if sox_breakdown is not None:
            detail_parts.append(f"SOX {sox_window[-1]:.0f}{'跌破' if sox_breakdown else '未跌破'}近{TECH_BREAKDOWN_LOOKBACK_DAYS}日支撐{sox_support:.0f}")
        if ndx_breakdown is not None:
            detail_parts.append(f"NDX {ndx_window[-1]:.0f}{'跌破' if ndx_breakdown else '未跌破'}近{TECH_BREAKDOWN_LOOKBACK_DAYS}日支撐{ndx_support:.0f}")
        detail = ("；".join(detail_parts) + f"；美債10Y {US10Y_FAST_RISE_LOOKBACK_DAYS}日變動 {us10y_change:+.2f}pp"
                  f"（{'達標' if us10y_fast_rise else '未達'} {US10Y_FAST_RISE_THRESHOLD}pp）")
    else:
        status, detail, score = None, "歷史資料不足或期間內有缺漏，尚無法判斷", None
    conditions.append(_condition("tech_capital_retreat", "科技資金退潮 (SOX/NDX跌破支撐+美債10Y快速攀升)", status, "full", detail, score))

    return conditions


def _bottom_conditions(history: List[Dict]) -> List[Dict]:
    conditions = []

    # B1. 恐慌極值反轉: VIX飆高後見頂回落 — 完整可驗證
    vix_window = _window(history, "vix", VIX_PEAK_LOOKBACK_DAYS)
    if vix_window is not None:
        peak = max(vix_window)
        today = vix_window[-1]
        status = peak > VIX_PEAK_THRESHOLD and today <= peak * VIX_ROLLOVER_RATIO
        rollover_ratio = today / peak if peak else None
        score = _avg(_graduated(peak, VIX_PEAK_SCALE), _graduated(rollover_ratio, VIX_ROLLOVER_RATIO_SCALE))
        detail = (f"近{VIX_PEAK_LOOKBACK_DAYS}日VIX高點 {peak:.1f}"
                  f"（{'>' if peak > VIX_PEAK_THRESHOLD else '<='} {VIX_PEAK_THRESHOLD}門檻）；"
                  f"目前 {today:.1f}（較高點回落 {(1 - today / peak) * 100:.0f}%，"
                  f"門檻 {(1 - VIX_ROLLOVER_RATIO) * 100:.0f}%）")
    else:
        status, detail, score = None, "歷史資料不足或期間內有缺漏，尚無法判斷", None
    conditions.append(_condition("vix_extreme_reversal", "恐慌極值反轉 (VIX飆高後見頂回落)", status, "full", detail, score))

    # B2. 散戶投降/融資斷頭: 融資餘額單日斷頭式大減 — 完整可驗證
    margin_amt_window = _window(history, "margin_balance_amount", MARGIN_CAPITULATION_LOOKBACK_DAYS + 1)
    if margin_amt_window is not None:
        diffs = [margin_amt_window[i] - margin_amt_window[i - 1] for i in range(1, len(margin_amt_window))]
        worst_drop = min(diffs) if diffs else 0
        status = worst_drop <= -MARGIN_CAPITULATION_DROP_NTB
        score = _graduated(worst_drop, MARGIN_CAPITULATION_SCALE)
        detail = (f"近{len(diffs)}個交易日融資餘額最大單日減幅 {worst_drop:.0f}億元"
                  f"（斷頭式門檻 -{MARGIN_CAPITULATION_DROP_NTB:.0f}億元）")
    else:
        status, detail, score = None, "歷史資料不足或期間內有缺漏，尚無法判斷", None
    conditions.append(_condition("margin_capitulation", "散戶投降/融資斷頭式大減", status, "full", detail, score))

    # B3. 外資空單回補與匯率止穩: 匯率止穩+現貨轉買+期貨空單減少 — 完整可驗證 (FinMind)
    usdtwd_window = _window(history, "usdtwd", TWD_DEPRECIATION_LOOKBACK_DAYS + 1)
    foreign_window = _window(history, "foreign_net", FOREIGN_RECENT_AVG_WINDOW + 1)
    futures_net_window = _window(history, "foreign_futures_net", FUTURES_COVERING_LOOKBACK_DAYS + 1)
    if usdtwd_window is not None and foreign_window is not None and futures_net_window is not None:
        fx_change = usdtwd_window[-1] - usdtwd_window[0]
        fx_stabilizing = fx_change <= 0
        foreign_today = foreign_window[-1]
        foreign_recent_avg = sum(foreign_window[:-1]) / len(foreign_window[:-1])
        foreign_flow_reversed = foreign_today > 0 and foreign_recent_avg < 0
        futures_change = futures_net_window[-1] - futures_net_window[0]  # less negative = covering
        futures_covering = futures_change >= FUTURES_COVERING_THRESHOLD
        status = fx_stabilizing and foreign_flow_reversed and futures_covering
        # Score reuses the same worked "Bottom Reversal Score" (30/35/35
        # split) computed by bottom_reversal_score() below, rather than a
        # separately-derived number — this condition IS that score's boolean
        # gate, so the two must never silently drift apart.
        reversal = bottom_reversal_score(history)
        score = reversal["total"] if reversal else None
        detail = (f"USD/TWD {TWD_DEPRECIATION_LOOKBACK_DAYS}日變動 {fx_change:+.3f}"
                  f"（{'止穩/升值' if fx_stabilizing else '仍在貶值'}）；"
                  f"外資今日{'轉買超' if foreign_today > 0 else '仍賣超'}"
                  f"，近期均值 {foreign_recent_avg:+.1f}億元；"
                  f"台指期淨部位{FUTURES_COVERING_LOOKBACK_DAYS}日變動 {futures_change:+.0f}口"
                  f"（{'回補中' if futures_covering else '未回補'}）")
    else:
        status, detail, score = None, "歷史資料不足或期間內有缺漏，尚無法判斷", None
    conditions.append(_condition("foreign_short_covering", "外資空單回補與匯率止穩", status, "full", detail, score))

    return conditions


def bottom_reversal_score(history: List[Dict]) -> Optional[Dict]:
    """
    B3 "Bottom Reversal Score" — a concrete worked example of turning a
    3-metric AND condition into its own weighted 0-100 score (30/35/35 split
    across FX stabilization / foreign spot flow reversal / TAIFEX futures
    short-covering), rather than the flat boolean B3 condition alone. Reuses
    the exact same windows B3 evaluates in _bottom_conditions() so the
    boolean gate and this score can never silently diverge on what data they
    look at. Returns None if the underlying windows aren't available yet.
    """
    usdtwd_window = _window(history, "usdtwd", TWD_DEPRECIATION_LOOKBACK_DAYS + 1)
    foreign_window = _window(history, "foreign_net", FOREIGN_RECENT_AVG_WINDOW + 1)
    futures_net_window = _window(history, "foreign_futures_net", FUTURES_COVERING_LOOKBACK_DAYS + 1)
    if usdtwd_window is None or foreign_window is None or futures_net_window is None:
        return None

    fx_change = usdtwd_window[-1] - usdtwd_window[0]
    foreign_today = foreign_window[-1]
    foreign_recent_avg = sum(foreign_window[:-1]) / len(foreign_window[:-1])
    futures_change = futures_net_window[-1] - futures_net_window[0]

    fx_score = _graduated(fx_change, FX_STABILIZATION_SCALE)
    foreign_score = _graduated(foreign_today - foreign_recent_avg, FOREIGN_REVERSAL_DELTA_SCALE)
    futures_score = _graduated(futures_change, FUTURES_COVERING_AMOUNT_SCALE)

    total = _weighted(
        (fx_score, BOTTOM_REVERSAL_WEIGHTS["fx_stabilization"]),
        (foreign_score, BOTTOM_REVERSAL_WEIGHTS["foreign_flow_reversal"]),
        (futures_score, BOTTOM_REVERSAL_WEIGHTS["futures_covering"]),
    )
    def _r(v):
        return round(v, 1) if v is not None else None

    return {
        "total": _r(total),
        "components": [
            {"name": "fx_stabilization", "weight": BOTTOM_REVERSAL_WEIGHTS["fx_stabilization"], "score": _r(fx_score)},
            {"name": "foreign_flow_reversal", "weight": BOTTOM_REVERSAL_WEIGHTS["foreign_flow_reversal"], "score": _r(foreign_score)},
            {"name": "futures_covering", "weight": BOTTOM_REVERSAL_WEIGHTS["futures_covering"], "score": _r(futures_score)},
        ],
    }


def _summarize(conditions: List[Dict]) -> Dict:
    evaluated = [c for c in conditions if c["status"] is not None]
    triggered = [c for c in evaluated if c["status"] is True]
    scored = [c["score"] for c in conditions if c["score"] is not None]
    return {
        "conditions": conditions,
        "total_conditions": len(conditions),
        "evaluated_count": len(evaluated),
        "triggered_count": len(triggered),
        "triggered_full_count": len([c for c in triggered if c["completeness"] == "full"]),
        "triggered_partial_count": len([c for c in triggered if c["completeness"] == "partial"]),
        "avg_score": round(sum(scored) / len(scored), 1) if scored else None,
    }


def evaluate_signal_confluence(history: List[Dict], min_history_days: int = 21) -> Dict:
    """
    Evaluate the top/bottom confluence conditions against the persisted daily
    macro/chip history.

    Args:
        history: list of daily snapshots (see main.py's _save_macro_history),
                 sorted ascending by date, most recent entry last.
        min_history_days: below this many days of history, don't even attempt
                 evaluation. Set to 21 (~1 month of trading days) to match the
                 longest individual condition window — T1's DXY breakout and
                 T5's SOX/NDX support breakdown both need a 20-day lookback
                 plus today (21 points). A lower gate (this used to be 6)
                 would flip 'available' to True while 2 of the 5 top
                 conditions still silently sit at "insufficient data" for two
                 more weeks — technically not wrong (each condition still
                 self-reports None honestly), but confusing: the panel claims
                 to be "on" while under-representing what it can actually see.
                 21 is the point where every condition (including B1/B2/B3's
                 now-tightened full-window requirements) can potentially
                 evaluate, so "available" means what it says.

    Returns a dict with 'available' (bool), 'as_of_date', and 'top'/'bottom'
    blocks (each from _summarize()). Individual conditions carry their own
    status of True/False/None(insufficient data) plus a 'completeness' of
    'full' or 'partial' — partial conditions are evaluated using only the
    data-available half of the original AND-condition and must be presented
    to the user as such, never conflated with a fully-verified trigger.
    """
    if len(history) < min_history_days:
        return {
            "available": False,
            "as_of_date": history[-1]["date"] if history else None,
            "history_days": len(history),
            "min_history_days": min_history_days,
            "note": f"歷史資料僅 {len(history)} 天，至少需要 {min_history_days} 天才開始評估（資料會隨每日執行自動累積）",
            "top": None,
            "bottom": None,
        }

    return {
        "available": True,
        "as_of_date": history[-1]["date"],
        "history_days": len(history),
        "top": _summarize(_top_conditions(history)),
        "bottom": _summarize(_bottom_conditions(history)),
        "bottom_reversal_score": bottom_reversal_score(history),
    }
