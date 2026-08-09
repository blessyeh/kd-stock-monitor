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
    DXY_BREAKOUT_LOOKBACK_DAYS,
    US10Y_FAST_RISE_LOOKBACK_DAYS,
    US10Y_FAST_RISE_THRESHOLD,
    TWD_DEPRECIATION_LOOKBACK_DAYS,
    TWD_DEPRECIATION_THRESHOLD,
    TWD_ROUND_NUMBER_STEP,
    MARGIN_NOT_RETREATING_LOOKBACK_DAYS,
    VIX_PEAK_LOOKBACK_DAYS,
    VIX_PEAK_THRESHOLD,
    VIX_ROLLOVER_RATIO,
    MARGIN_CAPITULATION_LOOKBACK_DAYS,
    MARGIN_CAPITULATION_DROP_NTB,
    FOREIGN_FUTURES_NET_SHORT_THRESHOLD,
    PUT_CALL_RATIO_LOW_THRESHOLD,
    FUTURES_COVERING_LOOKBACK_DAYS,
    FUTURES_COVERING_THRESHOLD,
    TECH_BREAKDOWN_LOOKBACK_DAYS,
    FOREIGN_RECENT_AVG_WINDOW,
)

# ── Additional thresholds specific to this module ────────────────────────
INDEX_BAND_PERIOD = 20         # Bollinger-style band period computed on TAIEX closes
INDEX_BAND_STD = 2.0
INDEX_RSI_PERIOD = 14
INDEX_RSI_OVERSOLD = 30.0
INDEX_RSI_OVERBOUGHT = 70.0
PERCENTILE_WINDOW = 120        # trailing sample size for VIX percentile-rank (Sentiment dimension)
MIN_HISTORY_DAYS = 21          # matches signal_confluence.py's evaluation gate


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

    # ── Macro (0-25): VIX stress/reversal + DXY easing off its recent high
    macro_pts, macro_notes = 0.0, []
    vix_peak_window = _window(history, "vix", VIX_PEAK_LOOKBACK_DAYS)
    if vix_peak_window is not None:
        peak, today = max(vix_peak_window), vix_peak_window[-1]
        if peak > VIX_PEAK_THRESHOLD and today <= peak * VIX_ROLLOVER_RATIO:
            macro_pts += 15
            macro_notes.append(f"VIX 已從近{VIX_PEAK_LOOKBACK_DAYS}日高點 {peak:.1f} 回落至 {today:.1f}（+15）")
        elif today > VIX_PEAK_THRESHOLD:
            macro_pts += 8
            macro_notes.append(f"VIX {today:.1f} 仍高於 {VIX_PEAK_THRESHOLD:.0f} 但尚未見頂回落（+8，訊號未完整）")
    dxy_window = _window(history, "dxy", DXY_BREAKOUT_LOOKBACK_DAYS + 1)
    if dxy_window is not None:
        dxy_high = max(dxy_window[:-1])
        if dxy_window[-1] < dxy_high:
            macro_pts += 10
            macro_notes.append(f"DXY {dxy_window[-1]:.2f} 未創近{DXY_BREAKOUT_LOOKBACK_DAYS}日新高（美元壓力未加劇，+10）")

    # ── Chip Flow (0-25): margin capitulation + foreign flow reversal
    chip_pts, chip_notes = 0.0, []
    margin_window = _window(history, "margin_balance_amount", MARGIN_CAPITULATION_LOOKBACK_DAYS + 1)
    if margin_window is not None:
        diffs = [margin_window[i] - margin_window[i - 1] for i in range(1, len(margin_window))]
        worst = min(diffs) if diffs else 0
        if worst <= -MARGIN_CAPITULATION_DROP_NTB:
            chip_pts += 15
            chip_notes.append(f"近{len(diffs)}日融資餘額最大單日減幅 {worst:.0f}億元（斷頭式，+15）")
    foreign_window = _window(history, "foreign_net", FOREIGN_RECENT_AVG_WINDOW + 1)
    if foreign_window is not None:
        foreign_today = foreign_window[-1]
        avg = sum(foreign_window[:-1]) / len(foreign_window[:-1])
        if foreign_today > 0 and avg < 0:
            chip_pts += 10
            chip_notes.append(f"外資今日轉買超，扭轉近{FOREIGN_RECENT_AVG_WINDOW}日均值賣超 {avg:+.1f}億元（+10）")

    # ── Derivative (0-20): futures short-covering + elevated PCR (hedging unwind potential)
    deriv_pts, deriv_notes = 0.0, []
    futures_window = _window(history, "foreign_futures_net", FUTURES_COVERING_LOOKBACK_DAYS + 1)
    if futures_window is not None:
        change = futures_window[-1] - futures_window[0]
        if change >= FUTURES_COVERING_THRESHOLD:
            deriv_pts += 12
            deriv_notes.append(f"台指期淨空單{FUTURES_COVERING_LOOKBACK_DAYS}日回補 {change:+.0f}口（+12）")
    pcr_today = _lookback(history, "put_call_ratio", 0)
    if pcr_today is not None and pcr_today > PUT_CALL_RATIO_LOW_THRESHOLD:
        deriv_pts += 8
        deriv_notes.append(f"P/C Ratio {pcr_today:.1f}% 偏高（避險需求濃厚，具反向支撐意涵，+8）")

    # ── Technical (0-20): TAIEX index-level band touch + RSI oversold
    tech_pts, tech_notes = 0.0, []
    band_window = _window(history, "taiex", INDEX_BAND_PERIOD)
    bands = _index_bands(band_window)
    if bands["lower"] is not None and taiex_today is not None and taiex_today <= bands["lower"] * 1.01:
        tech_pts += 12
        tech_notes.append(f"TAIEX {taiex_today:,.0f} 觸及/跌破{INDEX_BAND_PERIOD}日布林下軌 {bands['lower']:,.0f}（+12）")
    rsi_window = _window(history, "taiex", INDEX_RSI_PERIOD + 1)
    idx_rsi = _index_rsi(rsi_window)
    if idx_rsi is not None and idx_rsi <= INDEX_RSI_OVERSOLD:
        tech_pts += 8
        tech_notes.append(f"TAIEX {INDEX_RSI_PERIOD}日RSI {idx_rsi:.1f} 進入超賣區（+8）")

    # ── Sentiment (0-10): VIX percentile within its own trailing sample
    # (distributional stat — see _recent_values()'s docstring for why gap
    # tolerance is acceptable here specifically, unlike everywhere else).
    sent_pts, sent_notes = 0.0, []
    vix_sample = _recent_values(history, "vix", PERCENTILE_WINDOW)
    if vix_today is not None and len(vix_sample) >= 20:
        pct = _percentile_rank(vix_sample, vix_today)
        if pct is not None:
            if pct >= 80:
                sent_pts += 10
            elif pct >= 60:
                sent_pts += 5
            sent_notes.append(f"VIX 處於近{len(vix_sample)}筆歷史樣本的第 {pct:.0f} 百分位（愈高愈恐慌，滿分門檻80）")

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
    us10y_fast_rise = None
    if us10y_window is not None:
        us10y_fast_rise = us10y_window[-1] - us10y_window[0]
    us10y_hot = us10y_fast_rise is not None and us10y_fast_rise >= US10Y_FAST_RISE_THRESHOLD

    # ── Macro (0-25): DXY breakout + hot US10Y; SOX/NDX breakdown + hot US10Y
    macro_pts, macro_notes = 0.0, []
    dxy_window = _window(history, "dxy", DXY_BREAKOUT_LOOKBACK_DAYS + 1)
    if dxy_window is not None and us10y_hot:
        dxy_high = max(dxy_window[:-1])
        if dxy_window[-1] > dxy_high:
            macro_pts += 15
            macro_notes.append(f"DXY {dxy_window[-1]:.2f} 突破近{DXY_BREAKOUT_LOOKBACK_DAYS}日高點，美債10Y同步急升 {us10y_fast_rise:+.2f}pp（+15）")
    if us10y_hot:
        sox_window = _window(history, "sox", TECH_BREAKDOWN_LOOKBACK_DAYS + 1)
        ndx_window = _window(history, "ndx", TECH_BREAKDOWN_LOOKBACK_DAYS + 1)
        breakdown = False
        if sox_window is not None:
            breakdown = breakdown or sox_window[-1] < min(sox_window[:-1])
        if ndx_window is not None:
            breakdown = breakdown or ndx_window[-1] < min(ndx_window[:-1])
        if breakdown:
            macro_pts += 10
            macro_notes.append(f"SOX/NDX 跌破近{TECH_BREAKDOWN_LOOKBACK_DAYS}日支撐，美債10Y同步急升（+10）")

    # ── Chip Flow (0-25): TWD depreciation + foreign selling while margin stays stubborn
    chip_pts, chip_notes = 0.0, []
    twd_window = _window(history, "usdtwd", TWD_DEPRECIATION_LOOKBACK_DAYS + 1)
    if twd_window is not None:
        change = twd_window[-1] - twd_window[0]
        if change >= TWD_DEPRECIATION_THRESHOLD or _crossed_round_number(twd_window[-1], twd_window[0]):
            chip_pts += 10
            chip_notes.append(f"新台幣{TWD_DEPRECIATION_LOOKBACK_DAYS}日貶值 {change:+.3f}（+10）")
    margin_window = _window(history, "margin_balance_amount", MARGIN_NOT_RETREATING_LOOKBACK_DAYS + 1)
    foreign_today = _lookback(history, "foreign_net", 0)
    if margin_window is not None and foreign_today is not None:
        margin_stubborn = margin_window[-1] >= margin_window[0]
        if foreign_today < 0 and margin_stubborn:
            chip_pts += 15
            chip_notes.append(f"外資今日賣超，融資餘額{MARGIN_NOT_RETREATING_LOOKBACK_DAYS}日未回落（散戶尚未離場，+15）")

    # ── Derivative (0-20): heavy futures net-short + low PCR (complacency)
    deriv_pts, deriv_notes = 0.0, []
    futures_today = _lookback(history, "foreign_futures_net", 0)
    if futures_today is not None and futures_today <= -FOREIGN_FUTURES_NET_SHORT_THRESHOLD:
        deriv_pts += 12
        deriv_notes.append(f"外資台指期淨空單 {futures_today:+.0f}口，達 -{FOREIGN_FUTURES_NET_SHORT_THRESHOLD:.0f}口門檻（+12）")
    pcr_today = _lookback(history, "put_call_ratio", 0)
    if pcr_today is not None and pcr_today < PUT_CALL_RATIO_LOW_THRESHOLD:
        deriv_pts += 8
        deriv_notes.append(f"P/C Ratio {pcr_today:.1f}% 偏低（買權相對擁擠，市場偏樂觀，+8）")

    # ── Technical (0-20): TAIEX index-level band touch + RSI overbought
    tech_pts, tech_notes = 0.0, []
    band_window = _window(history, "taiex", INDEX_BAND_PERIOD)
    bands = _index_bands(band_window)
    if bands["upper"] is not None and taiex_today is not None and taiex_today >= bands["upper"] * 0.99:
        tech_pts += 12
        tech_notes.append(f"TAIEX {taiex_today:,.0f} 觸及{INDEX_BAND_PERIOD}日布林上軌 {bands['upper']:,.0f}（+12）")
    rsi_window = _window(history, "taiex", INDEX_RSI_PERIOD + 1)
    idx_rsi = _index_rsi(rsi_window)
    if idx_rsi is not None and idx_rsi >= INDEX_RSI_OVERBOUGHT:
        tech_pts += 8
        tech_notes.append(f"TAIEX {INDEX_RSI_PERIOD}日RSI {idx_rsi:.1f} 進入超買區（+8）")

    # ── Sentiment (0-10): VIX percentile — low percentile = complacency, a topping precursor
    sent_pts, sent_notes = 0.0, []
    vix_sample = _recent_values(history, "vix", PERCENTILE_WINDOW)
    if vix_today is not None and len(vix_sample) >= 20:
        pct = _percentile_rank(vix_sample, vix_today)
        if pct is not None:
            if pct <= 20:
                sent_pts += 10
            elif pct <= 40:
                sent_pts += 5
            sent_notes.append(f"VIX 處於近{len(vix_sample)}筆歷史樣本的第 {pct:.0f} 百分位（愈低愈自滿，滿分門檻20）")

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
