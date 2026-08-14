#!/usr/bin/env python3
"""
Signal Score — 0-100 量化評分（Bottom Setup Score / Top Risk Score）

Rationale: signal_confluence.py already evaluates 5 top conditions and 3
bottom conditions as independent booleans ("N / 5 項共振"), which is honest
but coarse — two conditions triggering out of five looks the same on the
dashboard whether they're the two weakest or the two strongest signals in
the set. This module re-expresses the same underlying market data as a
single 0-100 score per direction, split into five weighted dimensions
(Macro / Chip Flow / Derivative / Technical / Sentiment), so "the market is
somewhat bottom-supportive" becomes a comparable, ranked number instead of a
fraction.

IMPORTANT — what this score is NOT: it is still a hand-tuned, rule-based
weighting, exactly like every other threshold in this project. Turning a
boolean AND into a weighted sum does not, by itself, make it statistically
validated. Nothing here has been back-tested against historical TAIEX
returns yet (see README's "Signal History + Backtest" roadmap item — a
deliberately separate, not-yet-built module). Treat a score of "82/100" as
"82% of the hand-picked bottom-supportive conditions this project currently
tracks are present", not as "82% probability of a bounce". The dashboard
must carry this caveat next to the score, not just in this docstring.

Reuses signal_confluence.py's condition thresholds (DXY breakout window,
VIX peak/rollover, margin capitulation size, ...) AND its date-safe window
helpers (`_window` / `_lookback`) rather than redefining either, so the two
modules never silently drift apart on what counts as e.g. "a fast-rising
10-year yield" — or, previously, silently reintroduce the same date-gap bug
independently. This module used to have its own local `_series()` that
compacted out None values before taking the last N *values* positionally,
which (like signal_confluence.py's old `_series()`) could silently measure
a "5-day change" across a window that actually spanned 6 or 7 calendar days
because a gap day disappeared instead of blocking the window. Fixed
2026-08-09 by switching to the same `_window()`/`_lookback()` primitives
signal_confluence.py uses, which require an exact, fully-populated calendar
window or return None (insufficient data) rather than reaching further back
to compensate.
"""

from typing import Dict, List, Optional

from signal_confluence import (
    _window,
    _lookback,
    _graduated,
    _avg,
    _weighted,
    bottom_reversal_score,
    DXY_BREAKOUT_LOOKBACK_DAYS,
    US10Y_FAST_RISE_LOOKBACK_DAYS,
    TWD_DEPRECIATION_LOOKBACK_DAYS,
    TWD_ROUND_NUMBER_STEP,
    MARGIN_NOT_RETREATING_LOOKBACK_DAYS,
    VIX_PEAK_LOOKBACK_DAYS,
    MARGIN_CAPITULATION_LOOKBACK_DAYS,
    FUTURES_COVERING_LOOKBACK_DAYS,
    TECH_BREAKDOWN_LOOKBACK_DAYS,
    FOREIGN_RECENT_AVG_WINDOW,
    US10Y_FAST_RISE_SCALE,
    DXY_BREAKOUT_PCT_SCALE,
    TWD_DEPRECIATION_SCALE,
    FOREIGN_FLOW_AVG_SELL_SCALE,
    FUTURES_NET_SHORT_SCALE,
    MARGIN_STUBBORN_SCALE,
    PUT_CALL_RATIO_COMPLACENCY_SCALE,
    TECH_BREAKDOWN_PCT_SCALE,
    VIX_PEAK_SCALE,
    VIX_ROLLOVER_RATIO_SCALE,
    MARGIN_CAPITULATION_SCALE,
    FOREIGN_REVERSAL_DELTA_SCALE,
    FUTURES_COVERING_AMOUNT_SCALE,
)

# ── Additional thresholds specific to this module ────────────────────────
INDEX_BAND_PERIOD = 20         # Bollinger-style band period computed on TAIEX closes
INDEX_BAND_STD = 2.0
INDEX_RSI_PERIOD = 14
INDEX_RSI_OVERSOLD = 30.0
INDEX_RSI_OVERBOUGHT = 70.0
PERCENTILE_WINDOW = 120        # trailing sample size for VIX percentile-rank (Sentiment dimension)
MIN_HISTORY_DAYS = 21          # matches signal_confluence.py's evaluation gate

# ── Graduated 0-100 scales specific to this module's Technical/Sentiment
# dimensions (roadmap item 1 — same rationale as signal_confluence.py's own
# scales: a hard "touched the band" / "RSI<=30" check is a cliff; these
# replace it with piecewise-linear interpolation via the shared _graduated()
# helper imported above). Not shared with signal_confluence.py since these
# TAIEX index-level band/RSI reads don't have a boolean-condition counterpart
# there — the Technical dimension is a signal_score.py-only construct.
BAND_TOUCH_BOTTOM_SCALE = [(3.0, 0), (1.0, 20), (0.0, 55), (-1.0, 80), (-3.0, 100)]   # % vs lower band
BAND_TOUCH_TOP_SCALE = [(-3.0, 0), (-1.0, 20), (0.0, 55), (1.0, 80), (3.0, 100)]      # % vs upper band
RSI_OVERSOLD_SCALE = [(15, 100), (20, 85), (30, 55), (40, 25), (50, 0)]
RSI_OVERBOUGHT_SCALE = [(50, 0), (60, 25), (70, 55), (80, 85), (90, 100)]
SENTIMENT_BOTTOM_PERCENTILE_SCALE = [(40, 0), (60, 40), (80, 70), (95, 100)]  # higher pct = more fear
SENTIMENT_TOP_PERCENTILE_SCALE = [(5, 100), (20, 70), (40, 40), (60, 0)]      # lower pct = more complacent


def _recent_values(history: List[Dict], key: str, limit: int) -> List[float]:
    """
    Up to the last `limit` non-None values of `key`, most recent last — gaps
    are skipped rather than invalidating the whole set.

    This is intentionally more lenient than `_window()`/`_lookback()`
    (imported from signal_confluence.py) and must ONLY be used for
    distributional/statistical purposes that don't depend on the values
    being calendar-consecutive — e.g. percentile-rank, where "what fraction
    of past readings were at or below today's" is still meaningful even if
    a few days in between are missing. Never use this for a delta / streak
    / N-days-ago lookback — use `_window()` / `_lookback()` for those, since
    a gap there silently shifts what "N days" actually means.
    """
    vals = [h.get(key) for h in history if h.get(key) is not None]
    return vals[-limit:] if limit else vals


def _percentile_rank(series: List[float], value: float) -> Optional[float]:
    """% of the trailing window's values that are <= value. Used instead of
    an absolute VIX/PCR threshold for the Sentiment dimension, since a fixed
    number ("VIX > 30") drifts out of relevance across different volatility
    regimes over multi-year periods — a percentile self-adjusts."""
    if not series:
        return None
    return sum(1 for v in series if v <= value) / len(series) * 100


def _index_rsi(closes: Optional[List[float]], period: int = INDEX_RSI_PERIOD) -> Optional[float]:
    """closes must already be an exact, gap-free `period + 1`-length window
    (see _window()) — this function does no further trimming/validation."""
    if closes is None or len(closes) != period + 1:
        return None
    gains = [max(closes[i] - closes[i - 1], 0) for i in range(1, len(closes))]
    losses = [max(closes[i - 1] - closes[i], 0) for i in range(1, len(closes))]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _index_bands(closes: Optional[List[float]], num_std: float = INDEX_BAND_STD) -> Dict:
    """closes must already be an exact, gap-free window (see _window()) —
    this function does no further trimming/validation."""
    if closes is None or not closes:
        return {"upper": None, "lower": None}
    period = len(closes)
    mean = sum(closes) / period
    variance = sum((c - mean) ** 2 for c in closes) / period
    std = variance ** 0.5
    return {"upper": mean + num_std * std, "lower": mean - num_std * std}


def _crossed_round_number(today: float, prior: float, step: float = TWD_ROUND_NUMBER_STEP) -> bool:
    """Shared with signal_confluence.py's T2 condition — see that module's
    comment for why this is floor(value/step) rather than int(value)."""
    return today // step > prior // step


def _dim(name: str, cap: int, points: float, items: List[str]) -> Dict:
    points = round(min(cap, max(0, points)), 1)
    return {"name": name, "score": points, "cap": cap, "notes": items}


def _bottom_score(history: List[Dict]) -> Dict:
    taiex_today = _lookback(history, "taiex", 0)
    vix_today = _lookback(history, "vix", 0)
    dxy_today = _lookback(history, "dxy", 0)

    # ── Macro (0-25): VIX stress/reversal (graduated, cap 15) + DXY easing off its recent high (cap 10)
    macro_pts, macro_notes = 0.0, []
    vix_peak_window = _window(history, "vix", VIX_PEAK_LOOKBACK_DAYS)
    if vix_peak_window is not None:
        peak, today = max(vix_peak_window), vix_peak_window[-1]
        rollover_ratio = today / peak if peak else None
        vix_score = _avg(_graduated(peak, VIX_PEAK_SCALE), _graduated(rollover_ratio, VIX_ROLLOVER_RATIO_SCALE))
        if vix_score is not None:
            pts = 15 * vix_score / 100
            macro_pts += pts
            macro_notes.append(f"VIX 近{VIX_PEAK_LOOKBACK_DAYS}日高點 {peak:.1f} → 目前 {today:.1f}（強度 {vix_score:.0f}/100，+{pts:.1f}）")
    dxy_window = _window(history, "dxy", DXY_BREAKOUT_LOOKBACK_DAYS + 1)
    if dxy_window is not None:
        dxy_high = max(dxy_window[:-1])
        dxy_pct = (dxy_window[-1] - dxy_high) / dxy_high * 100 if dxy_high else None
        dxy_pressure = _graduated(dxy_pct, DXY_BREAKOUT_PCT_SCALE)  # higher = more dollar pressure (bad for bottom)
        if dxy_pressure is not None:
            dxy_score = 100 - dxy_pressure
            pts = 10 * dxy_score / 100
            macro_pts += pts
            macro_notes.append(f"DXY {dxy_window[-1]:.2f} 距近{DXY_BREAKOUT_LOOKBACK_DAYS}日高點 {dxy_pct:+.2f}%（美元壓力緩和強度 {dxy_score:.0f}/100，+{pts:.1f}）")

    # ── Chip Flow (0-25): margin capitulation (cap 15) + foreign flow reversal (cap 10);
    # reuses bottom_reversal_score()'s foreign-flow-reversal component so this dimension
    # and B3's worked example never silently diverge on what "reversal" means.
    chip_pts, chip_notes = 0.0, []
    margin_window = _window(history, "margin_balance_amount", MARGIN_CAPITULATION_LOOKBACK_DAYS + 1)
    if margin_window is not None:
        diffs = [margin_window[i] - margin_window[i - 1] for i in range(1, len(margin_window))]
        worst = min(diffs) if diffs else 0
        margin_score = _graduated(worst, MARGIN_CAPITULATION_SCALE)
        if margin_score is not None:
            pts = 15 * margin_score / 100
            chip_pts += pts
            chip_notes.append(f"近{len(diffs)}日融資餘額最大單日減幅 {worst:.0f}億元（斷頭強度 {margin_score:.0f}/100，+{pts:.1f}）")
    foreign_window = _window(history, "foreign_net", FOREIGN_RECENT_AVG_WINDOW + 1)
    if foreign_window is not None:
        foreign_today = foreign_window[-1]
        avg = sum(foreign_window[:-1]) / len(foreign_window[:-1])
        reversal_score = _graduated(foreign_today - avg, FOREIGN_REVERSAL_DELTA_SCALE)
        if reversal_score is not None:
            pts = 10 * reversal_score / 100
            chip_pts += pts
            chip_notes.append(f"外資今日 {foreign_today:+.1f}億元，較近{FOREIGN_RECENT_AVG_WINDOW}日均值 {avg:+.1f}億元（轉強強度 {reversal_score:.0f}/100，+{pts:.1f}）")

    # ── Derivative (0-20): futures short-covering (cap 12) + elevated PCR/hedging unwind potential (cap 8)
    deriv_pts, deriv_notes = 0.0, []
    futures_window = _window(history, "foreign_futures_net", FUTURES_COVERING_LOOKBACK_DAYS + 1)
    if futures_window is not None:
        change = futures_window[-1] - futures_window[0]
        futures_score = _graduated(change, FUTURES_COVERING_AMOUNT_SCALE)
        if futures_score is not None:
            pts = 12 * futures_score / 100
            deriv_pts += pts
            deriv_notes.append(f"台指期淨空單{FUTURES_COVERING_LOOKBACK_DAYS}日變動 {change:+.0f}口（回補強度 {futures_score:.0f}/100，+{pts:.1f}）")
    pcr_today = _lookback(history, "put_call_ratio", 0)
    if pcr_today is not None:
        pcr_complacency = _graduated(pcr_today, PUT_CALL_RATIO_COMPLACENCY_SCALE)  # higher = more complacent (bad for bottom)
        if pcr_complacency is not None:
            pcr_score = 100 - pcr_complacency
            pts = 8 * pcr_score / 100
            deriv_pts += pts
            deriv_notes.append(f"P/C Ratio {pcr_today:.1f}%（避險需求強度 {pcr_score:.0f}/100，+{pts:.1f}）")

    # ── Technical (0-20): TAIEX index-level band touch (cap 12) + RSI oversold (cap 8)
    tech_pts, tech_notes = 0.0, []
    band_window = _window(history, "taiex", INDEX_BAND_PERIOD)
    bands = _index_bands(band_window)
    if bands["lower"] is not None and taiex_today is not None:
        band_pct = (taiex_today - bands["lower"]) / bands["lower"] * 100
        band_score = _graduated(band_pct, BAND_TOUCH_BOTTOM_SCALE)
        if band_score is not None:
            pts = 12 * band_score / 100
            tech_pts += pts
            tech_notes.append(f"TAIEX {taiex_today:,.0f} 距{INDEX_BAND_PERIOD}日布林下軌 {bands['lower']:,.0f} {band_pct:+.2f}%（強度 {band_score:.0f}/100，+{pts:.1f}）")
    rsi_window = _window(history, "taiex", INDEX_RSI_PERIOD + 1)
    idx_rsi = _index_rsi(rsi_window)
    rsi_score = _graduated(idx_rsi, RSI_OVERSOLD_SCALE)
    if rsi_score is not None:
        pts = 8 * rsi_score / 100
        tech_pts += pts
        tech_notes.append(f"TAIEX {INDEX_RSI_PERIOD}日RSI {idx_rsi:.1f}（超賣強度 {rsi_score:.0f}/100，+{pts:.1f}）")

    # ── Sentiment (0-10): VIX percentile within its own trailing sample
    # (distributional stat — see _recent_values()'s docstring for why gap
    # tolerance is acceptable here specifically, unlike everywhere else).
    sent_pts, sent_notes = 0.0, []
    vix_sample = _recent_values(history, "vix", PERCENTILE_WINDOW)
    if vix_today is not None and len(vix_sample) >= 20:
        pct = _percentile_rank(vix_sample, vix_today)
        sent_score = _graduated(pct, SENTIMENT_BOTTOM_PERCENTILE_SCALE)
        if sent_score is not None:
            pts = 10 * sent_score / 100
            sent_pts += pts
            sent_notes.append(f"VIX 處於近{len(vix_sample)}筆歷史樣本的第 {pct:.0f} 百分位（恐慌強度 {sent_score:.0f}/100，+{pts:.1f}）")

    dims = [
        _dim("macro", 25, macro_pts, macro_notes),
        _dim("chip_flow", 25, chip_pts, chip_notes),
        _dim("derivative", 20, deriv_pts, deriv_notes),
        _dim("technical", 20, tech_pts, tech_notes),
        _dim("sentiment", 10, sent_pts, sent_notes),
    ]
    total = round(sum(d["score"] for d in dims), 1)
    return {"total": total, "dimensions": dims}


def _top_score(history: List[Dict]) -> Dict:
    taiex_today = _lookback(history, "taiex", 0)
    vix_today = _lookback(history, "vix", 0)

    us10y_window = _window(history, "us10y", US10Y_FAST_RISE_LOOKBACK_DAYS + 1)
    us10y_change = None
    if us10y_window is not None:
        us10y_change = us10y_window[-1] - us10y_window[0]
    us10y_score = _graduated(us10y_change, US10Y_FAST_RISE_SCALE)

    # ── Macro (0-25): DXY breakout (cap 15) + SOX/NDX breakdown (cap 10), each
    # averaged with the graduated US10Y-fast-rise score (mirrors T1/T5 in
    # signal_confluence.py — no more hard "hot or not" gate on US10Y).
    macro_pts, macro_notes = 0.0, []
    dxy_window = _window(history, "dxy", DXY_BREAKOUT_LOOKBACK_DAYS + 1)
    if dxy_window is not None and us10y_score is not None:
        dxy_high = max(dxy_window[:-1])
        dxy_pct = (dxy_window[-1] - dxy_high) / dxy_high * 100 if dxy_high else None
        combo = _avg(_graduated(dxy_pct, DXY_BREAKOUT_PCT_SCALE), us10y_score)
        if combo is not None:
            pts = 15 * combo / 100
            macro_pts += pts
            macro_notes.append(f"DXY {dxy_window[-1]:.2f} 距近{DXY_BREAKOUT_LOOKBACK_DAYS}日高點 {dxy_pct:+.2f}%，美債10Y{US10Y_FAST_RISE_LOOKBACK_DAYS}日變動 {us10y_change:+.2f}pp（強度 {combo:.0f}/100，+{pts:.1f}）")
    if us10y_score is not None:
        sox_window = _window(history, "sox", TECH_BREAKDOWN_LOOKBACK_DAYS + 1)
        ndx_window = _window(history, "ndx", TECH_BREAKDOWN_LOOKBACK_DAYS + 1)
        pct_candidates = []
        if sox_window is not None:
            sox_support = min(sox_window[:-1])
            if sox_support:
                pct_candidates.append((sox_window[-1] - sox_support) / sox_support * 100)
        if ndx_window is not None:
            ndx_support = min(ndx_window[:-1])
            if ndx_support:
                pct_candidates.append((ndx_window[-1] - ndx_support) / ndx_support * 100)
        if pct_candidates:
            tech_pct = min(pct_candidates)
            combo = _avg(_graduated(tech_pct, TECH_BREAKDOWN_PCT_SCALE), us10y_score)
            if combo is not None:
                pts = 10 * combo / 100
                macro_pts += pts
                macro_notes.append(f"SOX/NDX 距近{TECH_BREAKDOWN_LOOKBACK_DAYS}日支撐 {tech_pct:+.2f}%，美債10Y同步變動（強度 {combo:.0f}/100，+{pts:.1f}）")

    # ── Chip Flow (0-25): TWD depreciation (cap 10) + foreign selling while margin stays stubborn (cap 15)
    chip_pts, chip_notes = 0.0, []
    twd_window = _window(history, "usdtwd", TWD_DEPRECIATION_LOOKBACK_DAYS + 1)
    if twd_window is not None:
        change = twd_window[-1] - twd_window[0]
        crossed = _crossed_round_number(twd_window[-1], twd_window[0])
        base = _graduated(change, TWD_DEPRECIATION_SCALE)
        twd_score = max(base, 65) if crossed and base is not None else base
        if twd_score is not None:
            pts = 10 * twd_score / 100
            chip_pts += pts
            chip_notes.append(f"新台幣{TWD_DEPRECIATION_LOOKBACK_DAYS}日貶值 {change:+.3f}（強度 {twd_score:.0f}/100，+{pts:.1f}）")
    margin_window = _window(history, "margin_balance_amount", MARGIN_NOT_RETREATING_LOOKBACK_DAYS + 1)
    foreign_today = _lookback(history, "foreign_net", 0)
    if margin_window is not None and foreign_today is not None:
        margin_delta = margin_window[-1] - margin_window[0]
        combo = _weighted(
            (_graduated(foreign_today, FOREIGN_FLOW_AVG_SELL_SCALE), 40),
            (_graduated(margin_delta, MARGIN_STUBBORN_SCALE), 60),
        )
        if combo is not None:
            pts = 15 * combo / 100
            chip_pts += pts
            chip_notes.append(f"外資今日 {foreign_today:+.1f}億元，融資餘額{MARGIN_NOT_RETREATING_LOOKBACK_DAYS}日變動 {margin_delta:+.0f}億元（散戶未離場強度 {combo:.0f}/100，+{pts:.1f}）")

    # ── Derivative (0-20): heavy futures net-short (cap 12) + low PCR/complacency (cap 8)
    deriv_pts, deriv_notes = 0.0, []
    futures_today = _lookback(history, "foreign_futures_net", 0)
    futures_score = _graduated(futures_today, FUTURES_NET_SHORT_SCALE)
    if futures_score is not None:
        pts = 12 * futures_score / 100
        deriv_pts += pts
        deriv_notes.append(f"外資台指期淨空單 {futures_today:+.0f}口（強度 {futures_score:.0f}/100，+{pts:.1f}）")
    pcr_today = _lookback(history, "put_call_ratio", 0)
    pcr_score = _graduated(pcr_today, PUT_CALL_RATIO_COMPLACENCY_SCALE)
    if pcr_score is not None:
        pts = 8 * pcr_score / 100
        deriv_pts += pts
        deriv_notes.append(f"P/C Ratio {pcr_today:.1f}%（自滿強度 {pcr_score:.0f}/100，+{pts:.1f}）")

    # ── Technical (0-20): TAIEX index-level band touch (cap 12) + RSI overbought (cap 8)
    tech_pts, tech_notes = 0.0, []
    band_window = _window(history, "taiex", INDEX_BAND_PERIOD)
    bands = _index_bands(band_window)
    if bands["upper"] is not None and taiex_today is not None:
        band_pct = (taiex_today - bands["upper"]) / bands["upper"] * 100
        band_score = _graduated(band_pct, BAND_TOUCH_TOP_SCALE)
        if band_score is not None:
            pts = 12 * band_score / 100
            tech_pts += pts
            tech_notes.append(f"TAIEX {taiex_today:,.0f} 距{INDEX_BAND_PERIOD}日布林上軌 {bands['upper']:,.0f} {band_pct:+.2f}%（強度 {band_score:.0f}/100，+{pts:.1f}）")
    rsi_window = _window(history, "taiex", INDEX_RSI_PERIOD + 1)
    idx_rsi = _index_rsi(rsi_window)
    rsi_score = _graduated(idx_rsi, RSI_OVERBOUGHT_SCALE)
    if rsi_score is not None:
        pts = 8 * rsi_score / 100
        tech_pts += pts
        tech_notes.append(f"TAIEX {INDEX_RSI_PERIOD}日RSI {idx_rsi:.1f}（超買強度 {rsi_score:.0f}/100，+{pts:.1f}）")

    # ── Sentiment (0-10): VIX percentile — low percentile = complacency, a topping precursor
    sent_pts, sent_notes = 0.0, []
    vix_sample = _recent_values(history, "vix", PERCENTILE_WINDOW)
    if vix_today is not None and len(vix_sample) >= 20:
        pct = _percentile_rank(vix_sample, vix_today)
        sent_score = _graduated(pct, SENTIMENT_TOP_PERCENTILE_SCALE)
        if sent_score is not None:
            pts = 10 * sent_score / 100
            sent_pts += pts
            sent_notes.append(f"VIX 處於近{len(vix_sample)}筆歷史樣本的第 {pct:.0f} 百分位（自滿強度 {sent_score:.0f}/100，+{pts:.1f}）")

    dims = [
        _dim("macro", 25, macro_pts, macro_notes),
        _dim("chip_flow", 25, chip_pts, chip_notes),
        _dim("derivative", 20, deriv_pts, deriv_notes),
        _dim("technical", 20, tech_pts, tech_notes),
        _dim("sentiment", 10, sent_pts, sent_notes),
    ]
    total = round(sum(d["score"] for d in dims), 1)
    return {"total": total, "dimensions": dims}


def calculate_signal_scores(history: List[Dict], min_history_days: int = MIN_HISTORY_DAYS) -> Dict:
    """
    Compute the Bottom Setup Score and Top Risk Score (each 0-100, 5
    weighted dimensions) from persisted daily history.

    Returns:
        {
            "available": bool,
            "as_of_date": str or None,
            "bottom": {"total": float, "dimensions": [...]},
            "top": {"total": float, "dimensions": [...]},
            "caveat": str — the "this is not a backtested probability" disclaimer,
        }
    """
    caveat = ("本分數為規則式加權評分，尚未經過歷史資料回測驗證統計勝率，僅供比較「目前有多少項已知條件成立」，"
              "並非機率或勝率——回測與訊號事後績效追蹤為下一階段規劃項目。")
    if len(history) < min_history_days:
        return {
            "available": False,
            "as_of_date": history[-1]["date"] if history else None,
            "history_days": len(history),
            "min_history_days": min_history_days,
            "bottom": None,
            "top": None,
            "caveat": caveat,
        }

    return {
        "available": True,
        "as_of_date": history[-1]["date"],
        "history_days": len(history),
        "bottom": _bottom_score(history),
        "top": _top_score(history),
        "caveat": caveat,
    }
