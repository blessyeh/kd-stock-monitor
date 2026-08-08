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
put_call_ratio — _series() drops the missing values, so a condition just
reports "insufficient data" (status=None) until enough post-upgrade history
accumulates, rather than crashing or silently mis-scoring. The same applies
to sox/ndx (added alongside the T5 condition below).

Index choice note (T5): TWSE's weighted index is effectively a tech/
semiconductor-heavy index (TSMC + supply chain dominate its weighting), so
SOX and NDX are used as the "source pricing" leading indicators instead of
the Dow — the Dow's blue-chip/industrial composition has little correlation
with TW corporate earnings or capital flows.

This module only reads the persisted daily history (data/macro_history.json)
plus the module producing it — it doesn't fetch anything itself.
"""

from typing import Dict, List, Optional


# ── Tunable thresholds (documented, not hidden magic numbers) ───────────────
DXY_BREAKOUT_LOOKBACK_DAYS = 20      # "前高" = highest DXY close in the past N days
US10Y_FAST_RISE_LOOKBACK_DAYS = 5    # "快速攀升" window
US10Y_FAST_RISE_THRESHOLD = 0.15     # percentage points over that window
TWD_DEPRECIATION_LOOKBACK_DAYS = 5
TWD_DEPRECIATION_THRESHOLD = 0.3     # USD/TWD rising by this much = meaningful depreciation
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


def _series(history: List[Dict], key: str, window: Optional[int] = None) -> List[float]:
    """Extract a clean (non-None) value series for `key`, most recent last."""
    vals = [h.get(key) for h in history if h.get(key) is not None]
    if window is not None:
        vals = vals[-window:]
    return vals


def _condition(cid: str, label: str, status: Optional[bool], completeness: str, detail: str) -> Dict:
    # Defensive cast: every condition above computes `status` via comparisons
    # (>, >=, <, and/or) on values from history. main.py's _to_native() should
    # already keep numpy types out of that history, but this is the single
    # choke point all 8 conditions pass through — cheap insurance against a
    # numpy.bool_ (which json.dump() can't serialize) slipping into the
    # persisted summary from here or any future condition added later.
    if status is not None:
        status = bool(status)
    return {"id": cid, "label": label, "status": status, "completeness": completeness, "detail": detail}


def _top_conditions(history: List[Dict]) -> List[Dict]:
    conditions = []

    # T1. 宏觀資金抽離: DXY 突破前高 AND 美債10Y快速攀升 — 完整可驗證
    dxy_series = _series(history, "dxy")
    us10y_series = _series(history, "us10y")
    if len(dxy_series) >= DXY_BREAKOUT_LOOKBACK_DAYS + 1 and len(us10y_series) >= US10Y_FAST_RISE_LOOKBACK_DAYS + 1:
        dxy_today = dxy_series[-1]
        dxy_prior_high = max(dxy_series[-(DXY_BREAKOUT_LOOKBACK_DAYS + 1):-1])
        us10y_today = us10y_series[-1]
        us10y_change = us10y_today - us10y_series[-(US10Y_FAST_RISE_LOOKBACK_DAYS + 1)]
        dxy_breakout = dxy_today > dxy_prior_high
        us10y_fast_rise = us10y_change >= US10Y_FAST_RISE_THRESHOLD
        status = dxy_breakout and us10y_fast_rise
        detail = (f"DXY {dxy_today:.2f} vs 近{DXY_BREAKOUT_LOOKBACK_DAYS}日高點 {dxy_prior_high:.2f}"
                  f"（{'突破' if dxy_breakout else '未突破'}）；"
                  f"美債10Y {US10Y_FAST_RISE_LOOKBACK_DAYS}日變動 {us10y_change:+.2f}pp"
                  f"（{'達標' if us10y_fast_rise else '未達'} {US10Y_FAST_RISE_THRESHOLD}pp）")
    else:
        status, detail = None, "歷史資料不足，尚無法判斷"
    conditions.append(_condition("macro_drain", "宏觀資金抽離 (DXY突破前高+美債10Y快速攀升)", status, "full", detail))

    # T2. 匯率表態: 新台幣連續走貶 / 貶破整數關卡 — 完整可驗證
    usdtwd_series = _series(history, "usdtwd")
    if len(usdtwd_series) >= TWD_DEPRECIATION_LOOKBACK_DAYS + 1:
        today = usdtwd_series[-1]
        prior = usdtwd_series[-(TWD_DEPRECIATION_LOOKBACK_DAYS + 1)]
        change = today - prior
        crossed_round_number = int(today) > int(prior)
        status = change >= TWD_DEPRECIATION_THRESHOLD or crossed_round_number
        detail = (f"USD/TWD {TWD_DEPRECIATION_LOOKBACK_DAYS}日變動 {change:+.3f}"
                  f"（貶值門檻 {TWD_DEPRECIATION_THRESHOLD}）"
                  + ("；期間貶破整數關卡" if crossed_round_number else ""))
    else:
        status, detail = None, "歷史資料不足，尚無法判斷"
    conditions.append(_condition("twd_depreciation", "匯率表態 (新台幣連續走貶/貶破關卡)", status, "full", detail))

    # T3. 外資期現貨雙空: 現貨連續賣超 + 台指期淨空單達門檻 — 完整可驗證 (FinMind)
    foreign_series = _series(history, "foreign_net")
    futures_net_series = _series(history, "foreign_futures_net")
    if len(foreign_series) >= FOREIGN_SELL_STREAK_DAYS and futures_net_series:
        recent = foreign_series[-FOREIGN_SELL_STREAK_DAYS:]
        spot_sell_streak = all(v < 0 for v in recent)
        futures_net_today = futures_net_series[-1]
        futures_heavy_short = futures_net_today <= -FOREIGN_FUTURES_NET_SHORT_THRESHOLD
        status = spot_sell_streak and futures_heavy_short
        detail = (f"外資現貨連續{FOREIGN_SELL_STREAK_DAYS}日賣超："
                  f"{'是' if spot_sell_streak else '否'}（{[round(v,1) for v in recent]}億元）；"
                  f"台指期淨部位 {futures_net_today:+.0f}口"
                  f"（{'達' if futures_heavy_short else '未達'} -{FOREIGN_FUTURES_NET_SHORT_THRESHOLD:.0f}口門檻）")
    else:
        status, detail = None, "歷史資料不足，尚無法判斷"
    conditions.append(_condition("foreign_dual_short", "外資期現貨雙空", status, "full", detail))

    # T4. 籌碼過度樂觀/散戶接刀: 外資賣超+融資不退+P/C Ratio<100% — 完整可驗證 (FinMind)
    margin_amt_series = _series(history, "margin_balance_amount")
    pc_ratio_series = _series(history, "put_call_ratio")
    if (foreign_series and pc_ratio_series
            and len(margin_amt_series) >= MARGIN_NOT_RETREATING_LOOKBACK_DAYS + 1):
        foreign_selling_today = foreign_series[-1] < 0
        margin_not_retreating = margin_amt_series[-1] >= margin_amt_series[-(MARGIN_NOT_RETREATING_LOOKBACK_DAYS + 1)]
        pc_ratio_today = pc_ratio_series[-1]
        pc_ratio_low = pc_ratio_today < PUT_CALL_RATIO_LOW_THRESHOLD
        status = foreign_selling_today and margin_not_retreating and pc_ratio_low
        detail = (f"今日外資{'賣超' if foreign_selling_today else '買超'}；"
                  f"融資餘額{MARGIN_NOT_RETREATING_LOOKBACK_DAYS}日"
                  f"{'未回落' if margin_not_retreating else '已回落'}"
                  f"（{margin_amt_series[-1]:.0f}億元）；"
                  f"P/C Ratio {pc_ratio_today:.1f}%"
                  f"（{'<' if pc_ratio_low else '>='} {PUT_CALL_RATIO_LOW_THRESHOLD:.0f}%門檻）")
    else:
        status, detail = None, "歷史資料不足，尚無法判斷"
    conditions.append(_condition("retail_holding_bag", "籌碼過度樂觀/散戶接刀", status, "full", detail))

    # T5. 科技資金退潮: 費半(SOX)或那斯達克100(NDX)跌破近期支撐 AND 美債10Y快速攀升
    # — 完整可驗證。台股加權指數本質是「科技/半導體重壓指數」（台積電及供應鏈佔絕對
    # 權重），SOX/NDX 的轉折是台股轉折的源頭定價，比道瓊等傳產指數更有預測力，因此
    # 用「跌破支撐」而非「跌幅」來定義：只要兩者之一跌破近 N 日低點，視為結構轉弱。
    sox_series = _series(history, "sox")
    ndx_series = _series(history, "ndx")
    if (len(us10y_series) >= US10Y_FAST_RISE_LOOKBACK_DAYS + 1
            and (len(sox_series) >= TECH_BREAKDOWN_LOOKBACK_DAYS + 1
                 or len(ndx_series) >= TECH_BREAKDOWN_LOOKBACK_DAYS + 1)):
        us10y_today = us10y_series[-1]
        us10y_change = us10y_today - us10y_series[-(US10Y_FAST_RISE_LOOKBACK_DAYS + 1)]
        us10y_fast_rise = us10y_change >= US10Y_FAST_RISE_THRESHOLD

        sox_breakdown = None
        if len(sox_series) >= TECH_BREAKDOWN_LOOKBACK_DAYS + 1:
            sox_today = sox_series[-1]
            sox_support = min(sox_series[-(TECH_BREAKDOWN_LOOKBACK_DAYS + 1):-1])
            sox_breakdown = sox_today < sox_support

        ndx_breakdown = None
        if len(ndx_series) >= TECH_BREAKDOWN_LOOKBACK_DAYS + 1:
            ndx_today = ndx_series[-1]
            ndx_support = min(ndx_series[-(TECH_BREAKDOWN_LOOKBACK_DAYS + 1):-1])
            ndx_breakdown = ndx_today < ndx_support

        tech_breakdown = bool(sox_breakdown) or bool(ndx_breakdown)
        status = tech_breakdown and us10y_fast_rise
        detail_parts = []
        if sox_breakdown is not None:
            detail_parts.append(f"SOX {sox_series[-1]:.0f}{'跌破' if sox_breakdown else '未跌破'}近{TECH_BREAKDOWN_LOOKBACK_DAYS}日支撐{sox_support:.0f}")
        if ndx_breakdown is not None:
            detail_parts.append(f"NDX {ndx_series[-1]:.0f}{'跌破' if ndx_breakdown else '未跌破'}近{TECH_BREAKDOWN_LOOKBACK_DAYS}日支撐{ndx_support:.0f}")
        detail = ("；".join(detail_parts) + f"；美債10Y {US10Y_FAST_RISE_LOOKBACK_DAYS}日變動 {us10y_change:+.2f}pp"
                  f"（{'達標' if us10y_fast_rise else '未達'} {US10Y_FAST_RISE_THRESHOLD}pp）")
    else:
        status, detail = None, "歷史資料不足，尚無法判斷"
    conditions.append(_condition("tech_capital_retreat", "科技資金退潮 (SOX/NDX跌破支撐+美債10Y快速攀升)", status, "full", detail))

    return conditions


def _bottom_conditions(history: List[Dict]) -> List[Dict]:
    conditions = []

    # B1. 恐慌極值反轉: VIX飆高後見頂回落 — 完整可驗證
    vix_series = _series(history, "vix", window=VIX_PEAK_LOOKBACK_DAYS)
    # Require the window to actually be full before calling anything a "10-day
    # peak" — with only 2-3 points, "peak" is just whichever days happened to
    # be collected first, not a real recent high.
    if len(vix_series) >= VIX_PEAK_LOOKBACK_DAYS:
        peak = max(vix_series)
        today = vix_series[-1]
        status = peak > VIX_PEAK_THRESHOLD and today <= peak * VIX_ROLLOVER_RATIO
        detail = (f"近{VIX_PEAK_LOOKBACK_DAYS}日VIX高點 {peak:.1f}"
                  f"（{'>' if peak > VIX_PEAK_THRESHOLD else '<='} {VIX_PEAK_THRESHOLD}門檻）；"
                  f"目前 {today:.1f}（較高點回落 {(1 - today / peak) * 100:.0f}%，"
                  f"門檻 {(1 - VIX_ROLLOVER_RATIO) * 100:.0f}%）")
    else:
        status, detail = None, "歷史資料不足，尚無法判斷"
    conditions.append(_condition("vix_extreme_reversal", "恐慌極值反轉 (VIX飆高後見頂回落)", status, "full", detail))

    # B2. 散戶投降/融資斷頭: 融資餘額單日斷頭式大減 — 完整可驗證
    margin_amt_series = _series(history, "margin_balance_amount", window=MARGIN_CAPITULATION_LOOKBACK_DAYS + 1)
    # Same reasoning as B1: require the full comparison window, not just 2
    # points, so "近5個交易日最大單日減幅" is measured over an actual 5 days.
    if len(margin_amt_series) >= MARGIN_CAPITULATION_LOOKBACK_DAYS + 1:
        diffs = [margin_amt_series[i] - margin_amt_series[i - 1] for i in range(1, len(margin_amt_series))]
        worst_drop = min(diffs) if diffs else 0
        status = worst_drop <= -MARGIN_CAPITULATION_DROP_NTB
        detail = (f"近{len(diffs)}個交易日融資餘額最大單日減幅 {worst_drop:.0f}億元"
                  f"（斷頭式門檻 -{MARGIN_CAPITULATION_DROP_NTB:.0f}億元）")
    else:
        status, detail = None, "歷史資料不足，尚無法判斷"
    conditions.append(_condition("margin_capitulation", "散戶投降/融資斷頭式大減", status, "full", detail))

    # B3. 外資空單回補與匯率止穩: 匯率止穩+現貨轉買+期貨空單減少 — 完整可驗證 (FinMind)
    usdtwd_series = _series(history, "usdtwd")
    foreign_series = _series(history, "foreign_net")
    futures_net_series = _series(history, "foreign_futures_net", window=FUTURES_COVERING_LOOKBACK_DAYS + 1)
    # Require the full comparison windows (not just 2 points) so "近期均值"
    # and the futures-covering delta are measured over their actual windows,
    # same reasoning as B1/B2 above.
    if (len(usdtwd_series) >= TWD_DEPRECIATION_LOOKBACK_DAYS + 1
            and len(foreign_series) >= FOREIGN_RECENT_AVG_WINDOW + 1
            and len(futures_net_series) >= FUTURES_COVERING_LOOKBACK_DAYS + 1):
        fx_change = usdtwd_series[-1] - usdtwd_series[-(TWD_DEPRECIATION_LOOKBACK_DAYS + 1)]
        fx_stabilizing = fx_change <= 0
        recent_window = foreign_series[-(FOREIGN_RECENT_AVG_WINDOW + 1):-1]
        foreign_recent_avg = sum(recent_window) / len(recent_window)
        foreign_flow_reversed = foreign_series[-1] > 0 and foreign_recent_avg < 0
        futures_change = futures_net_series[-1] - futures_net_series[0]  # less negative = covering
        futures_covering = futures_change >= FUTURES_COVERING_THRESHOLD
        status = fx_stabilizing and foreign_flow_reversed and futures_covering
        detail = (f"USD/TWD {TWD_DEPRECIATION_LOOKBACK_DAYS}日變動 {fx_change:+.3f}"
                  f"（{'止穩/升值' if fx_stabilizing else '仍在貶值'}）；"
                  f"外資今日{'轉買超' if foreign_series[-1] > 0 else '仍賣超'}"
                  f"，近期均值 {foreign_recent_avg:+.1f}億元；"
                  f"台指期淨部位{len(futures_net_series)-1}日變動 {futures_change:+.0f}口"
                  f"（{'回補中' if futures_covering else '未回補'}）")
    else:
        status, detail = None, "歷史資料不足，尚無法判斷"
    conditions.append(_condition("foreign_short_covering", "外資空單回補與匯率止穩", status, "full", detail))

    return conditions


def _summarize(conditions: List[Dict]) -> Dict:
    evaluated = [c for c in conditions if c["status"] is not None]
    triggered = [c for c in evaluated if c["status"] is True]
    return {
        "conditions": conditions,
        "total_conditions": len(conditions),
        "evaluated_count": len(evaluated),
        "triggered_count": len(triggered),
        "triggered_full_count": len([c for c in triggered if c["completeness"] == "full"]),
        "triggered_partial_count": len([c for c in triggered if c["completeness"] == "partial"]),
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
    }
