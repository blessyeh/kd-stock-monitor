#!/usr/bin/env python3
"""
Market Report — 自動產生的每日市場分析報告（繁體中文）

Turns the numeric snapshots fetcher.py / signal_confluence.py / signal_score.py /
risk_engine.py already compute into short, readable sentences, grouped into
sections (國際市場總覽 / 台股籌碼面總覽 / 風險訊號摘要 / 綜合觀察). Rule-based
only — this runs unattended inside the GitHub Actions pipeline, so every
sentence is template text filled from already-fetched official data, never a
guessed interpretation of a number that wasn't actually retrieved.

Scope note: 國際市場一節只讀取 fetch_macro_indicators() 已追蹤的欄位（VIX/美債
10Y/美元指數/比特幣/原油/黃金/費半/那指100/標普500）；台股籌碼面一節只讀取
fetch_tw_chip_indicators() 已追蹤的欄位。本模組不新增資料來源、不臆測任何未抓取
到的數值 —— 缺值的項目直接跳過該句，不會用猜測值填補。
"""

from datetime import datetime
from typing import Dict, List, Optional

import signal_confluence as _sc  # reuse documented thresholds, never redefine them


def _fmt_pct(v: Optional[float]) -> str:
    return "N/A" if v is None else f"{v:+.2f}%"


def _trend_word(change_pct: Optional[float], big: float, small: float) -> str:
    """Magnitude classifier — thresholds are per-indicator (see INTL_ITEMS),
    since e.g. a 5% VIX move is routine but a 5% S&P 500 move is historic."""
    if change_pct is None:
        return "持平"
    if change_pct >= big:
        return "大幅上升"
    if change_pct >= small:
        return "上升"
    if change_pct <= -big:
        return "大幅下跌"
    if change_pct <= -small:
        return "下跌"
    return "持平"


# (key in macro dict, label, value format, big-move %, small-move %, risk meaning)
# risk meaning: "high_bad" = rising value is a risk-off signal (VIX/DXY/US10Y);
# "high_good" = rising value is risk-on for TW tech (SOX/NDX/SP500);
# "neutral" = no directional risk read attached (BTC/Oil/Gold trade on their own drivers).
INTL_ITEMS = [
    ("fear_greed", "VIX恐慌指數", "{:.2f}", 15.0, 5.0, "high_bad"),
    ("us10y", "美債10年期殖利率", "{:.2f}%", 3.0, 1.0, "high_bad"),
    ("dxy", "美元指數(DXY)", "{:.2f}", 1.0, 0.3, "high_bad"),
    ("btc", "比特幣", "${:,.0f}", 5.0, 2.0, "neutral"),
    ("oil", "WTI原油", "${:.2f}", 4.0, 1.5, "neutral"),
    ("gold", "黃金", "${:,.0f}", 3.0, 1.0, "neutral"),
    ("sox", "費城半導體指數(SOX)", "{:,.0f}", 4.0, 1.5, "high_good"),
    ("ndx", "那斯達克100(NDX)", "{:,.0f}", 3.0, 1.0, "high_good"),
    ("sp500", "標普500(S&P 500)", "{:,.0f}", 2.0, 0.7, "high_good"),
]

_TAIL_CLAUSE = {
    ("high_bad", "大幅上升"): "，為風險偏好轉弱的訊號",
    ("high_bad", "大幅下跌"): "，顯示該項風險指標降溫",
    ("high_good", "大幅上升"): "，顯示風險偏好回升",
    ("high_good", "大幅下跌"): "，顯示風險偏好轉弱",
}


def _describe_intl(macro: Dict) -> List[str]:
    lines = []
    for key, label, fmt, big, small, meaning in INTL_ITEMS:
        d = (macro or {}).get(key) or {}
        value, chg_pct = d.get("value"), d.get("change_pct")
        if value is None:
            continue
        trend = _trend_word(chg_pct, big, small)
        tail = _TAIL_CLAUSE.get((meaning, trend), "")
        lines.append(f"{label}報{fmt.format(value)}，{trend}{_fmt_pct(chg_pct)}{tail}。")
    return lines


def _describe_tw_chip(chip: Dict) -> List[str]:
    chip = chip or {}
    lines = []

    foreign = chip.get("foreign_net") or {}
    if foreign.get("value") is not None:
        v = foreign["value"]
        word = "買超" if v >= 0 else "賣超"
        extra = "，賣壓明顯放大" if v <= -100 else ("，買盤力道強勁" if v >= 100 else "")
        lines.append(f"外資今日{word} {abs(v):,.1f} 億元{extra}。")

    trust = chip.get("trust_net") or {}
    if trust.get("value") is not None:
        v = trust["value"]
        word = "買超" if v >= 0 else "賣超"
        lines.append(f"投信今日{word} {abs(v):,.1f} 億元。")

    margin = chip.get("margin_balance") or {}
    if margin.get("value") is not None:
        chg_pct = margin.get("change_pct")
        trend = _trend_word(chg_pct, 3.0, 1.0)
        capitulation = "，疑似出現融資斷頭賣壓" if chg_pct is not None and chg_pct <= -5 else ""
        lines.append(f"融資餘額約 {margin['value'] / 10000:,.1f} 萬張，{trend}{_fmt_pct(chg_pct)}{capitulation}。")

    ratio = chip.get("margin_short_ratio") or {}
    if ratio.get("value") is not None:
        note = "（偏低，做空籌碼相對有限）" if ratio["value"] < 1 else ""
        lines.append(f"資券比 {ratio['value']:.2f}%{note}。")

    usdtwd = chip.get("usdtwd") or chip.get("usdtwd_cbc") or {}
    if usdtwd.get("value") is not None:
        chg = usdtwd.get("change")
        if chg and chg > 0:
            direction = f"貶值 {chg:.3f}"
        elif chg and chg < 0:
            direction = f"升值 {abs(chg):.3f}"
        else:
            direction = "持平"
        lines.append(f"新台幣兌美元報 {usdtwd['value']:.3f}，{direction}。")

    futures = chip.get("foreign_futures_net_taifex") or chip.get("foreign_futures_net") or {}
    if futures.get("value") is not None:
        v = futures["value"]
        word = "淨多單" if v >= 0 else "淨空單"
        heavy = "，空單規模達到「期現貨雙空」觀察的量級門檻" if v <= -_sc.FOREIGN_FUTURES_NET_SHORT_THRESHOLD else ""
        lines.append(f"外資台指期{word} {abs(v):,.0f} 口{heavy}。")

    pcr = chip.get("put_call_ratio") or {}
    if pcr.get("value") is not None:
        v = pcr["value"]
        note = "（低於100%，偏向做多/樂觀氣氛）" if v < _sc.PUT_CALL_RATIO_LOW_THRESHOLD else "（避險/看跌需求偏高）"
        lines.append(f"選擇權P/C比 {v:.2f}%{note}。")

    return lines


def _describe_signals(confluence: Dict, signal_score: Dict, risk_score: Dict) -> List[str]:
    lines = []

    if confluence and confluence.get("available"):
        top = confluence.get("top") or {}
        bottom = confluence.get("bottom") or {}
        triggered_top = [c["label"] for c in (top.get("conditions") or []) if c.get("status") is True]
        triggered_bottom = [c["label"] for c in (bottom.get("conditions") or []) if c.get("status") is True]
        if triggered_top:
            lines.append(f"訊號共振（轉折觀察）目前觸發 {len(triggered_top)} 項頂部訊號：{'、'.join(triggered_top)}。")
        if triggered_bottom:
            lines.append(f"訊號共振目前觸發 {len(triggered_bottom)} 項底部訊號：{'、'.join(triggered_bottom)}。")
        if not triggered_top and not triggered_bottom:
            lines.append("訊號共振模型目前無頂部或底部條件觸發。")
    else:
        lines.append("訊號共振模型歷史資料尚不足，暫無法評估。")

    if signal_score and signal_score.get("available"):
        top_total = (signal_score.get("top") or {}).get("total")
        bottom_total = (signal_score.get("bottom") or {}).get("total")
        if top_total is not None:
            lines.append(f"頂部風險分數 {top_total:.0f}/100。")
        if bottom_total is not None:
            lines.append(f"底部佈局分數 {bottom_total:.0f}/100。")

    if risk_score and risk_score.get("available"):
        lines.append(
            f"台股上市市場綜合風險評分 {risk_score['score']:.0f}/100"
            f"（{risk_score.get('risk_level')}：{risk_score.get('risk_level_desc')}），"
            f"資料覆蓋率 {risk_score.get('coverage_pct')}%。"
        )
    elif risk_score and risk_score.get("coverage_pct") is not None:
        lines.append(
            f"台股上市市場綜合風險評分資料覆蓋率僅 {risk_score.get('coverage_pct')}%"
            f"（需達80%才會正式評分），暫無法提供綜合分數。"
        )

    return lines


_HEADLINES = {
    "risk_high": "風險偏高：國際與台股籌碼面同步出現避險訊號，短線宜留意波動加大",
    "risk_low_opportunity": "出現底部訊號：部分籌碼面轉強條件成立，但仍需等待更多確認",
    "neutral": "訊號中性：目前尚未出現明顯頂部或底部共振訊號",
}

_CONCLUSIONS = {
    "risk_high": "綜合國際市場避險情緒與台股籌碼面變化，短線風險偏高，建議留意持股波動與資金配置，"
                 "但本報告非放空或出清建議。",
    "risk_low_opportunity": "部分底部訊號浮現，但訊號尚未達到高度共振，建議持續觀察而非立即大幅加碼。",
    "neutral": "目前市場訊號大致中性，未見顯著的頂部或底部共振，建議維持既定投資紀律。",
}


def _tone(confluence: Dict, risk_score: Dict) -> str:
    top_n = ((confluence or {}).get("top") or {}).get("triggered_count") or 0
    bottom_n = ((confluence or {}).get("bottom") or {}).get("triggered_count") or 0
    if risk_score and risk_score.get("available") and risk_score.get("score", 0) >= 60:
        return "risk_high"
    if top_n >= 2:
        return "risk_high"
    if bottom_n >= 2:
        return "risk_low_opportunity"
    return "neutral"


def generate_market_report(macro: Dict, chip: Dict, confluence: Dict = None,
                            signal_score: Dict = None, risk_score: Dict = None,
                            regime: Dict = None) -> Dict:
    """
    Build today's auto-generated Chinese-language market report from data the
    pipeline already computed this run. Never fetches anything itself.
    """
    intl_lines = _describe_intl(macro)
    tw_lines = _describe_tw_chip(chip)
    signal_lines = _describe_signals(confluence, signal_score, risk_score)
    if regime and regime.get("available"):
        signal_lines.insert(0, f"目前市場狀態判定為「{regime.get('regime_label')}」。")

    tone = _tone(confluence, risk_score)

    return {
        "available": True,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "generated_at": datetime.now().isoformat(),
        "headline": _HEADLINES[tone],
        "tone": tone,
        "sections": [
            {"id": "international", "title": "國際市場總覽", "lines": intl_lines},
            {"id": "tw_chip", "title": "台股籌碼面總覽", "lines": tw_lines},
            {"id": "signals", "title": "風險訊號摘要", "lines": signal_lines},
            {"id": "conclusion", "title": "綜合觀察", "lines": [_CONCLUSIONS[tone]]},
        ],
        "disclaimer": "本報告為規則式自動生成之市場數據摘要，依現有已核實資料模板化產生文字，"
                       "非投資建議、不構成買賣訊號，請勿單獨作為交易依據。",
    }
