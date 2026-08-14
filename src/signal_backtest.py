#!/usr/bin/env python3
"""
Signal History + Backtest — roadmap item 2.

Nothing in this project has ever logged what a signal said on a given day and
then checked what actually happened afterward, so nobody can compute a real
win rate / expectancy / Sharpe for any of signal_confluence.py's conditions,
signal_score.py's threshold crossings, or tsmc_analyzer.py's buy-point
setups. This module is the missing piece: it appends one row per trading day
to a persisted log (data/signal_history.json, written by main.py, mirroring
_save_macro_history's one-entry-per-calendar-date pattern), then recomputes
forward-return statistics against that log on every run.

IMPORTANT — cold start, read before treating any number here as meaningful:
this can only accumulate *forward* from the day it first ships. There is no
way to reconstruct what signal_confluence.py / signal_score.py would have
said on a past date — only raw indicator values are in macro_history.json,
not each day's derived condition/score results, and this project's rule
definitions have changed over time anyway. Every stat below reports
`insufficient_sample: true` until MIN_BACKTEST_SAMPLE occurrences exist at a
given horizon — the same graceful "not enough data yet" pattern used
throughout this codebase (e.g. signal_confluence's 21-day gate), not a bug.

What "max drawdown" means here: these are independent, possibly-overlapping
signal occurrences, not a sequential trade log, so a real compounded
equity-curve drawdown isn't well-defined. `worst_case_return` is reported
instead — the single worst-oriented forward return seen among the
occurrences at that horizon — and is documented as such rather than
overclaiming a portfolio-level drawdown number.
"""

import statistics
from typing import Dict, List, Optional

HORIZONS = [1, 3, 5, 10, 20]  # trading days ahead (entries in signal_history.json, not calendar days)
MIN_BACKTEST_SAMPLE = 10      # below this many occurrences at a horizon, report insufficient_sample
MAX_LOG_ENTRIES = 500         # ~2 years of trading days

TOP_CONDITION_IDS = ["macro_drain", "twd_depreciation", "foreign_dual_short",
                      "retail_holding_bag", "tech_capital_retreat"]
BOTTOM_CONDITION_IDS = ["vix_extreme_reversal", "margin_capitulation", "foreign_short_covering"]
TSMC_BUY_POINT_IDS = ["fundamental_pullback", "trend_breakout", "panic_reversal"]

CAVEAT = ("回測樣本仍在累積中，且訊號規則本身仍為人為設定的權重（詳見 Signal Score / TSMC 分數頁的相同警語）。"
          "勝率/期望值/Sharpe 僅反映本專案自建立回測記錄以來的實際訊號表現，並非對未來的保證，"
          "亦無法回溯本專案上線前的歷史資料。")


def record_signal_snapshot(signal_log: List[Dict], date: str, taiex: Optional[float],
                            stock_2330_close: Optional[float], confluence_result: Optional[Dict],
                            signal_score_result: Optional[Dict], regime_result: Optional[Dict],
                            tsmc_analysis: Optional[Dict]) -> List[Dict]:
    """
    Build today's signal-state row and upsert it into signal_log (overwrite
    if an entry for `date` already exists — same reasoning as
    _save_macro_history: repeated hourly runs on the same day must collapse
    into one row, not one per run). Returns the updated, sorted, truncated
    list — callers should persist this back to data/signal_history.json.
    """
    top = (confluence_result or {}).get("top") or {}
    bottom = (confluence_result or {}).get("bottom") or {}
    top_conditions = {c["id"]: c["status"] for c in top.get("conditions", [])}
    bottom_conditions = {c["id"]: c["status"] for c in bottom.get("conditions", [])}

    ss_top = (signal_score_result or {}).get("top") or {}
    ss_bottom = (signal_score_result or {}).get("bottom") or {}

    buy_points = [bp["id"] for bp in (tsmc_analysis or {}).get("buy_points", []) or []]

    entry = {
        "date": date,
        "taiex": taiex,
        "stock_2330_close": stock_2330_close,
        "top_conditions": top_conditions,
        "bottom_conditions": bottom_conditions,
        "top_score": ss_top.get("total"),
        "bottom_score": ss_bottom.get("total"),
        "regime": (regime_result or {}).get("regime"),
        "tsmc_total": (tsmc_analysis or {}).get("total"),
        "tsmc_buy_points": buy_points,
    }

    existing_idx = next((i for i, e in enumerate(signal_log) if e.get("date") == date), None)
    if existing_idx is not None:
        signal_log[existing_idx] = entry
    else:
        signal_log.append(entry)

    signal_log.sort(key=lambda e: e.get("date") or "")
    return signal_log[-MAX_LOG_ENTRIES:]


def _signal_definitions() -> List[Dict]:
    """
    Every signal type tracked for backtesting: (id, label, direction,
    price_ref, trigger(entry)->bool). `direction` decides how a forward
    return is scored as a win — 'top' signals (hedge/sell calls) win when
    price falls afterward, 'bottom' signals (buy/add calls) win when price
    rises afterward. `price_ref` picks which price series to measure the
    forward return against — TAIEX for market-wide signals, 2330's own close
    for TSMC-specific buy-points.
    """
    defs = []
    for cid in TOP_CONDITION_IDS:
        defs.append({"id": cid, "label": cid, "direction": "top", "price_ref": "taiex",
                     "trigger": (lambda e, cid=cid: e["top_conditions"].get(cid) is True)})
    for cid in BOTTOM_CONDITION_IDS:
        defs.append({"id": cid, "label": cid, "direction": "bottom", "price_ref": "taiex",
                     "trigger": (lambda e, cid=cid: e["bottom_conditions"].get(cid) is True)})
    defs.append({"id": "top_score_ge_70", "label": "頂部風險分數 ≥ 70", "direction": "top", "price_ref": "taiex",
                 "trigger": (lambda e: e.get("top_score") is not None and e["top_score"] >= 70)})
    defs.append({"id": "bottom_score_ge_70", "label": "底部佈局分數 ≥ 70", "direction": "bottom", "price_ref": "taiex",
                 "trigger": (lambda e: e.get("bottom_score") is not None and e["bottom_score"] >= 70)})
    for bp_id in TSMC_BUY_POINT_IDS:
        defs.append({"id": f"tsmc_{bp_id}", "label": f"TSMC {bp_id}", "direction": "bottom",
                     "price_ref": "stock_2330_close",
                     "trigger": (lambda e, bp_id=bp_id: bp_id in (e.get("tsmc_buy_points") or []))})
    return defs


def _horizon_stats(returns_oriented: List[float]) -> Dict:
    n = len(returns_oriented)
    if n < MIN_BACKTEST_SAMPLE:
        return {"sample_size": n, "insufficient_sample": True}
    wins = [r for r in returns_oriented if r > 0]
    avg_return = sum(returns_oriented) / n
    stdev = statistics.pstdev(returns_oriented) if n > 1 else 0.0
    return {
        "sample_size": n,
        "insufficient_sample": False,
        "win_rate": round(len(wins) / n * 100, 1),
        "avg_return": round(avg_return, 2),
        "expectancy": round(avg_return, 2),  # oriented return already nets wins vs. losses by frequency+magnitude
        "worst_case_return": round(min(returns_oriented), 2),
        "sharpe": round(avg_return / stdev, 2) if stdev > 0 else None,
    }


def compute_backtest_stats(signal_log: List[Dict]) -> Dict:
    """
    Recompute forward-return statistics for every tracked signal type against
    the full persisted log. Cheap to run every time (the log stays under
    MAX_LOG_ENTRIES rows) so this always reflects the latest occurrence, not
    an incrementally-stale cache.
    """
    if not signal_log:
        return {"available": False, "as_of_date": None, "log_days": 0, "signals": {}, "caveat": CAVEAT}

    signals_out = {}
    for d in _signal_definitions():
        horizons_out = {}
        for h in HORIZONS:
            oriented_returns = []
            for i, entry in enumerate(signal_log):
                if i + h >= len(signal_log):
                    continue
                if not d["trigger"](entry):
                    continue
                entry_price = entry.get(d["price_ref"])
                future_price = signal_log[i + h].get(d["price_ref"])
                if entry_price is None or future_price is None or entry_price == 0:
                    continue
                raw_return = (future_price - entry_price) / entry_price * 100
                oriented = raw_return if d["direction"] == "bottom" else -raw_return
                oriented_returns.append(oriented)
            horizons_out[str(h)] = _horizon_stats(oriented_returns)
        signals_out[d["id"]] = {"label": d["label"], "direction": d["direction"], "horizons": horizons_out}

    return {
        "available": True,
        "as_of_date": signal_log[-1]["date"],
        "log_days": len(signal_log),
        "signals": signals_out,
        "caveat": CAVEAT,
    }
