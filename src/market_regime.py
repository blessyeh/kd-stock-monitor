#!/usr/bin/env python3
"""
Market Regime Detection — 大盤狀態判斷

Rationale (see README "Market Regime + Signal Score" section for the full
discussion): the same raw reading means different things in different market
environments. VIX>30 during a bull-market correction is historically a buy
signal; the same VIX>30 at the start of a bear trend is often just the
beginning of a much larger drop. KD<=20 on an individual stock during a bull
correction is a high-quality dip; KD<=20 during a confirmed bear trend is
frequently a falling knife. Every other module in this project (alert
filters, signal confluence, per-stock scoring) evaluates its conditions the
same way regardless of the broader backdrop — this module supplies that
missing backdrop classification so the others can condition on it.

Five regimes, in order of detection precedence (a Panic reading pre-empts
the trend classification; a Recovery reading pre-empts a stale Bear label
even before the long moving average has caught up):

    PANIC            VIX spiking fast and already elevated — acute stress,
                      regardless of where price sits relative to its average.
    RECOVERY         Coming out of Panic/Bear: VIX has rolled over from a
                      recent peak AND foreign capital flow is reversing from
                      net-sell to net-buy. A transitional state, not a
                      confirmed uptrend yet.
    BULL_TREND       Price above its long moving average AND that average
                      is itself still rising.
    BULL_CORRECTION  Price above its long moving average, but the average
                      has flattened/turned down — an uptrend digesting a
                      pullback, not (yet) reversing.
    BEAR_TREND       Price below its long moving average, with none of the
                      Recovery conditions present.

Data source: the same persisted daily history this whole project already
relies on for signal_confluence.py (data/macro_history.json's 'taiex',
'vix', 'foreign_net' fields) — no new fetching required.

MA period is adaptive rather than hard-coded to 200 days: backfill_macro_
history() only seeds ~35 trading days of history on first run, and it takes
several months of daily accumulation to reach a full 200-day window. Using a
fixed MA200 would leave this module reporting UNKNOWN for most of a year.
Instead it uses the longest MA period from a fixed ladder the available
history can actually support, and always reports which period it used so
nothing is silently under-powered.

Date-alignment note (fixed 2026-08-09): all lookback/window reads below go
through signal_confluence.py's `_window()` / `_lookback()` helpers rather
than a local compacted-list scan — see that module's docstring for why a
gap inside a lookback window has to invalidate the window instead of being
silently skipped (a missing day used to shift what "200-day MA" or "5-day
VIX change" actually measured, without either function knowing).
"""

from typing import Dict, List

from signal_confluence import _window, _lookback

# ── Tunable thresholds (documented, not hidden magic numbers) ───────────────
MA_PERIOD_LADDER = [200, 120, 60, 20]   # tries longest first, degrades gracefully
MA_SLOPE_LOOKBACK_DAYS = 20             # "均線上彎/走平" comparison window
VIX_SPIKE_THRESHOLD = 30.0              # shared convention with signal_confluence.py
VIX_FAST_RISE_LOOKBACK_DAYS = 5
VIX_FAST_RISE_POINTS = 5.0              # VIX rising this many points within the window = acute panic
VIX_PEAK_LOOKBACK_DAYS = 10
VIX_ROLLOVER_RATIO = 0.85               # current VIX <= 85% of the recent peak = "已見頂回落"
FOREIGN_RECOVERY_LOOKBACK_DAYS = 5      # window for "近期均值仍為賣超" in the Recovery check
TAIEX_SHORT_TERM_LOOKBACK_DAYS = 5      # used only in the human-readable detail text

REGIME_LABELS = {
    "BULL_TREND": "多頭趨勢",
    "BULL_CORRECTION": "多頭回檔",
    "BEAR_TREND": "空頭趨勢",
    "PANIC": "恐慌急殺",
    "RECOVERY": "築底回穩",
    "UNKNOWN": "資料不足",
}

# What each regime implies for interpreting a per-stock KD extreme —
# consumed by alert_checker.py so the same raw KD reading gets a different
# confirmation bar depending on backdrop. Kept here (not in alert_checker.py)
# so the mapping from regime -> interpretation stays next to the regime
# definitions themselves.
REGIME_OVERSOLD_BIAS = {
    "BULL_TREND": "neutral",       # KD rarely reaches oversold in a strong uptrend; treat normally
    "BULL_CORRECTION": "favor",    # textbook "buy the dip" backdrop — lower the confirmation bar
    "RECOVERY": "favor",           # stabilizing after stress — oversold readings more credible
    "BEAR_TREND": "distrust",      # raise the bar — oversold can stay oversold for a long time
    "PANIC": "distrust",           # falling knife risk is highest here
    "UNKNOWN": "neutral",
}
REGIME_OVERBOUGHT_BIAS = {
    "BULL_TREND": "distrust",      # strong uptrends stay "overbought" for weeks — don't fight it
    "BULL_CORRECTION": "neutral",
    "RECOVERY": "neutral",
    "BEAR_TREND": "favor",         # rallies in a downtrend are the classic sucker's rally
    "PANIC": "favor",
    "UNKNOWN": "neutral",
}


def _pick_ma_windows(history: List[Dict], key: str = "taiex"):
    """
    Longest period in MA_PERIOD_LADDER for which BOTH an exact, gap-free
    `period`-day window ending today AND one ending MA_SLOPE_LOOKBACK_DAYS
    ago are available — returns (period, now_window, prior_window), or
    (None, None, None) if even the shortest period can't be satisfied.

    The "prior" window is computed against `history[:-MA_SLOPE_LOOKBACK_DAYS]`
    — dropping the most recent MA_SLOPE_LOOKBACK_DAYS calendar entries first,
    then taking the trailing `period`-day window of what's left — rather than
    slicing a pre-compacted values list, so it actually lands
    MA_SLOPE_LOOKBACK_DAYS calendar days back, not however-many-points-back a
    gap happened to leave it at.
    """
    for period in MA_PERIOD_LADDER:
        now_window = _window(history, key, period)
        if now_window is None:
            continue
        if len(history) <= MA_SLOPE_LOOKBACK_DAYS:
            continue
        prior_window = _window(history[:-MA_SLOPE_LOOKBACK_DAYS], key, period)
        if prior_window is None:
            continue
        return period, now_window, prior_window
    return None, None, None


def detect_market_regime(history: List[Dict]) -> Dict:
    """
    Classify the current market regime from persisted daily history.

    Returns:
        {
            "available": bool,
            "as_of_date": str or None,
            "regime": one of REGIME_LABELS keys,
            "regime_label": Chinese label,
            "ma_period_used": int or None — which MA period the trend read used,
            "detail": human-readable string explaining the classification,
            "metrics": dict of the raw numbers behind the decision (for the
                       dashboard / debugging — mirrors signal_confluence.py's
                       'detail' transparency convention),
        }
    """
    as_of_date = history[-1]["date"] if history else None

    ma_period, ma_now_window, ma_prior_window = _pick_ma_windows(history, "taiex")
    if ma_period is None:
        taiex_days = sum(1 for h in history if h.get("taiex") is not None)
        return {
            "available": False,
            "as_of_date": as_of_date,
            "regime": "UNKNOWN",
            "regime_label": REGIME_LABELS["UNKNOWN"],
            "ma_period_used": None,
            "detail": f"TAIEX 歷史資料僅 {taiex_days} 天（且/或期間內有缺漏），尚不足以判斷任何均線週期的市場狀態（資料會隨每日執行自動累積）",
            "metrics": {},
        }

    price_today = _lookback(history, "taiex", 0)
    ma_now = sum(ma_now_window) / len(ma_now_window)
    ma_prior = sum(ma_prior_window) / len(ma_prior_window)
    above_ma = price_today is not None and price_today > ma_now
    ma_rising = ma_now > ma_prior

    # VIX-based panic / recovery signals (reuses the same peak/rollover idea
    # as signal_confluence.py's B1 condition, computed independently here
    # since this module classifies a persistent regime, not a one-off event).
    vix_today = _lookback(history, "vix", 0)
    vix_fast_rise_window = _window(history, "vix", VIX_FAST_RISE_LOOKBACK_DAYS + 1)
    vix_fast_rise = (vix_fast_rise_window[-1] - vix_fast_rise_window[0]) if vix_fast_rise_window is not None else None
    vix_peak_window = _window(history, "vix", VIX_PEAK_LOOKBACK_DAYS)
    vix_recent_peak = max(vix_peak_window) if vix_peak_window is not None else None
    vix_rolled_over = (
        vix_today is not None and vix_recent_peak is not None
        and vix_recent_peak > VIX_SPIKE_THRESHOLD and vix_today <= vix_recent_peak * VIX_ROLLOVER_RATIO
    )

    foreign_window = _window(history, "foreign_net", FOREIGN_RECOVERY_LOOKBACK_DAYS + 1)
    foreign_reversing = False
    foreign_recent_avg = None
    if foreign_window is not None:
        foreign_today = foreign_window[-1]
        foreign_recent_avg = sum(foreign_window[:-1]) / len(foreign_window[:-1])
        foreign_reversing = foreign_today > 0 and foreign_recent_avg < 0

    metrics = {
        "taiex": round(price_today, 2) if price_today is not None else None,
        "ma_now": round(ma_now, 2) if ma_now is not None else None,
        "ma_prior": round(ma_prior, 2) if ma_prior is not None else None,
        "above_ma": above_ma,
        "ma_rising": ma_rising,
        "vix_today": vix_today,
        "vix_fast_rise": round(vix_fast_rise, 2) if vix_fast_rise is not None else None,
        "vix_recent_peak": vix_recent_peak,
        "vix_rolled_over": vix_rolled_over,
        "foreign_recent_avg": round(foreign_recent_avg, 2) if foreign_recent_avg is not None else None,
        "foreign_reversing": foreign_reversing,
    }

    # ── Classification (precedence order matters) ───────────────────────
    is_panic = (
        vix_today is not None and vix_fast_rise is not None
        and vix_today > VIX_SPIKE_THRESHOLD and vix_fast_rise >= VIX_FAST_RISE_POINTS
    )
    is_recovery = (
        not is_panic
        and (not above_ma or (vix_recent_peak is not None and vix_recent_peak > VIX_SPIKE_THRESHOLD))
        and vix_rolled_over
        and foreign_reversing
    )

    if is_panic:
        regime = "PANIC"
        detail = (f"VIX {vix_today:.1f} 高於 {VIX_SPIKE_THRESHOLD:.0f} 門檻，且近{VIX_FAST_RISE_LOOKBACK_DAYS}日"
                   f"急升 {vix_fast_rise:+.1f} 點（門檻 {VIX_FAST_RISE_POINTS:.0f} 點）— 判定為急性恐慌")
    elif is_recovery:
        regime = "RECOVERY"
        detail = (f"VIX 自近{VIX_PEAK_LOOKBACK_DAYS}日高點 {vix_recent_peak:.1f} 回落至 {vix_today:.1f}"
                   f"（回落逾 {(1 - VIX_ROLLOVER_RATIO) * 100:.0f}%），且外資今日轉買超"
                   f"（近{FOREIGN_RECOVERY_LOOKBACK_DAYS}日均值仍為賣超 {foreign_recent_avg:+.1f} 億元）"
                   f"— 判定為壓力後築底回穩")
    elif above_ma and ma_rising:
        regime = "BULL_TREND"
        detail = f"TAIEX {price_today:,.0f} 站上 {ma_period}日均線 {ma_now:,.0f} 且均線仍上揚 — 判定為多頭趨勢"
    elif above_ma and not ma_rising:
        regime = "BULL_CORRECTION"
        detail = f"TAIEX {price_today:,.0f} 仍在 {ma_period}日均線 {ma_now:,.0f} 之上，但均線走平/下彎 — 判定為多頭回檔（而非趨勢反轉）"
    else:
        regime = "BEAR_TREND"
        detail = f"TAIEX {price_today:,.0f} 跌破 {ma_period}日均線 {ma_now:,.0f}，且未觀察到回穩訊號 — 判定為空頭趨勢"

    return {
        "available": True,
        "as_of_date": as_of_date,
        "regime": regime,
        "regime_label": REGIME_LABELS[regime],
        "ma_period_used": ma_period,
        "detail": detail,
        "metrics": metrics,
    }


def oversold_bias(regime: str) -> str:
    """'favor' / 'neutral' / 'distrust' — how this regime should shift the
    confirmation bar for a per-stock KD oversold reading. See REGIME_OVERSOLD_BIAS."""
    return REGIME_OVERSOLD_BIAS.get(regime, "neutral")


def overbought_bias(regime: str) -> str:
    """Same idea as oversold_bias(), for KD overbought readings."""
    return REGIME_OVERBOUGHT_BIAS.get(regime, "neutral")
