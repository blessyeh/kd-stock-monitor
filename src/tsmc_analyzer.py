#!/usr/bin/env python3
"""
Single-Stock Investment Score — 五層模型：基本面 × 市場預期(以自身財測代理) × 技術面 × 籌碼 × 大盤環境

Originally built for TSMC (2330) alone — this project's single largest,
most-watched holding, where treating it like any other ticker (KD/MACD/
institutional-flow each judged in isolation) misses the thing that actually
moves its price most: TSMC usually trades *ahead* of its own reported
results, on revisions to future earnings expectations (monthly revenue
trend, and the forward guidance given at each quarterly earnings call), not
on the trailing quarter's numbers alone. A pure technical/KD read of 2330 is
structurally blind to that.

calculate_stock_investment_score() below generalizes the same 10-dimension
model to any tracked stock with FinMind fundamentals coverage (see
calculate_tsmc_score() for 2330's own thin wrapper, and the module-level
has_adr/relative_strength_benchmarks docs on calculate_stock_investment_score()
for what does/doesn't carry over to a non-2330 name). Two dimensions stay
structurally TSMC-only and cleanly degrade to "not applicable" elsewhere:
Guidance (no other tracked company has a free, automatable official-guidance
source integrated) and ADR Premium/Discount (no other tracked company has a
US ADR sister listing in this project's watchlist).

Scores 8-10 dimensions (100 points total; Guidance/ADR unavailable = "not
applicable" for a non-2330 stock, same graceful degrade as any other thin
data source), each independently degrading to "insufficient data" rather
than crashing or guessing when a data source is short:

    Revenue Momentum       15   monthly revenue YoY + 3-month trend/acceleration
    Margin / EPS Trend     10   gross margin momentum + EPS growth (quality, not just growth)
    Guidance                15   own-guidance QoQ revision(6) + revenue beat/miss(5) + margin beat/miss(4)
    Technical Trend         15   MA20/60/120 stack structure
    Momentum (composite)    10   KD+RSI+MACD averaged into ONE score, not summed (see below)
    Relative Strength       10   2330 vs TAIEX / SOX / NDX
    Institutional / Chip    10   foreign flow x price direction (confirm vs. divergence vs. absorption)
    ADR Premium/Discount     5   2330 vs TSM ADR implied price
    Market Regime             5   from market_regime.py — same signal means different things in different regimes
    Valuation                 5   trailing PER percentile within 2330's own 3-year history

IMPORTANT — the "Momentum composite" dimension is deliberately an AVERAGE of
KD/RSI/MACD's existing 0-100 scores (from scoring_engine.py), not a sum of
three separately-weighted lines. KD, RSI, and MACD are all derived from the
same underlying price series and are highly correlated — summing three
correlated readings as if they were three independent confirmations
overstates confidence ("three indicators agree" isn't three times more
reliable than one, when the three aren't actually independent).

IMPORTANT — what's NOT here: true analyst consensus estimates (Street
revenue/EPS forecasts) are not available from any free, reliably
point-in-time source, so this module never fetches or uses Consensus.
TSMC's own structured Guidance figures, however, ARE free and automatable —
see fetcher.fetch_tsmc_official_guidance() (scrapes investor.tsmc.com's own
quarterly-results page) and main.py's _update_tsmc_guidance_auto(), which
together replaced what used to be a fully-manual data/tsmc_guidance.json
(that file is now just a fallback seed for quarters predating the
auto-fetch). What this module does instead of Consensus is compare TSMC's
own guidance to ITS OWN prior guidance (Guidance Revision) and to its own
subsequent actuals (Guidance beat/miss) — every such figure is tagged
benchmark_type="GUIDANCE" and must never be conflated with a future
Consensus source if one is ever added.

IMPORTANT — like signal_score.py, this is a hand-tuned rule-based weighting,
not a back-tested statistical model. Treat "82/100" as "82 points' worth of
this project's tracked bullish conditions are currently present", not as a
probability of any particular return. See README's Roadmap for the planned
Signal History + Backtest module that would eventually validate (or correct)
these weights against actual forward 2330 returns.
"""

from typing import Dict, List, Optional

from market_regime import REGIME_LABELS

# ── Tunable thresholds ────────────────────────────────────────────────────
REVENUE_YOY_STRONG = 30.0
REVENUE_YOY_MODERATE = 15.0
EPS_YOY_STRONG = 20.0
RS_LOOKBACK_DAYS = 20
INSTITUTIONAL_FLOW_THRESHOLD = 500_000   # shares, 3-day cumulative — matches alert_checker.py's convention
ADR_RATIO = 5                            # 1 TSM ADR = 5 TSMC ordinary shares (public, fixed by depositary agreement)
VALUATION_PERCENTILE_CHEAP = 30
VALUATION_PERCENTILE_EXPENSIVE = 85

RECOMMENDATION_BANDS = [
    (80, "強勢加碼區"),
    (65, "偏多持有"),
    (50, "中性持有"),
    (35, "減碼/等待"),
    (0, "防守"),
]


def _recommendation(total: float) -> str:
    for threshold, label in RECOMMENDATION_BANDS:
        if total >= threshold:
            return label
    return RECOMMENDATION_BANDS[-1][1]


def _dim(name: str, cap: float, points: Optional[float], notes: List[str]) -> Dict:
    if points is None:
        return {"name": name, "score": None, "cap": cap, "available": False, "notes": notes}
    return {"name": name, "score": round(min(cap, max(0, points)), 1), "cap": cap, "available": True, "notes": notes}


def _percentile_rank(series: List[float], value: float) -> float:
    return sum(1 for v in series if v <= value) / len(series) * 100


# ── Dimension 1: Revenue Momentum (0-15) ────────────────────────────────────
def _score_revenue_momentum(monthly_revenue: List[Dict]) -> Dict:
    notes = []
    if len(monthly_revenue) < 16:
        return _dim("revenue_momentum", 15, None, ["月營收歷史不足16個月，尚無法計算3個月YoY移動趨勢"])

    by_ym = {(r["year"], r["month"]): r["revenue_ntd"] for r in monthly_revenue}

    def yoy(year: int, month: int) -> Optional[float]:
        cur = by_ym.get((year, month))
        prev = by_ym.get((year - 1, month))
        if cur is None or prev is None or prev == 0:
            return None
        return (cur - prev) / prev * 100

    latest = monthly_revenue[-3:]
    yoys_now = [yoy(r["year"], r["month"]) for r in latest]
    if any(v is None for v in yoys_now):
        return _dim("revenue_momentum", 15, None, ["近3個月缺乏去年同期資料，尚無法計算YoY"])
    avg_now = sum(yoys_now) / 3

    prior_3 = monthly_revenue[-4:-1]
    yoys_prior = [yoy(r["year"], r["month"]) for r in prior_3]
    avg_prior = sum(yoys_prior) / 3 if all(v is not None for v in yoys_prior) else None
    accelerating = avg_prior is not None and avg_now > avg_prior

    notes.append(f"近3個月營收YoY：{[round(v,1) for v in yoys_now]}，3個月均值 {avg_now:+.1f}%"
                 + (f"（較前期 {avg_prior:+.1f}% {'加速' if accelerating else '減速'}）" if avg_prior is not None else ""))

    if avg_now >= REVENUE_YOY_STRONG and (accelerating or avg_prior is None):
        pts = 15
    elif avg_now >= REVENUE_YOY_STRONG:
        pts = 10
        notes.append("營收年增仍強勁，但動能較前期放緩——營收好不代表趨勢仍在加速")
    elif avg_now >= REVENUE_YOY_MODERATE:
        pts = 7
    elif avg_now >= 0:
        pts = 3
    else:
        pts = 0
    return _dim("revenue_momentum", 15, pts, notes)


# ── Dimension 2: Margin / EPS Trend (0-10) ──────────────────────────────────
def _score_margin_eps(quarterly: List[Dict]) -> Dict:
    if len(quarterly) < 2:
        return _dim("margin_eps_trend", 10, None, ["季度財報歷史不足2季，尚無法計算毛利率動能"])

    def gm(q):
        r, g = q.get("revenue_ntd"), q.get("gross_profit_ntd")
        return (g / r * 100) if r and g is not None else None

    latest, prev = quarterly[-1], quarterly[-2]
    gm_latest, gm_prev = gm(latest), gm(prev)
    if gm_latest is None or gm_prev is None:
        return _dim("margin_eps_trend", 10, None, ["缺少毛利率所需的營收/毛利資料"])
    gm_momentum = gm_latest - gm_prev

    eps_latest = latest.get("eps")
    eps_yoy = None
    yoy_match = next((q for q in quarterly if q["date"][:4] == str(int(latest["date"][:4]) - 1) and q["date"][5:7] == latest["date"][5:7]), None)
    if eps_latest is not None and yoy_match and yoy_match.get("eps"):
        eps_yoy = (eps_latest - yoy_match["eps"]) / abs(yoy_match["eps"]) * 100

    notes = [f"毛利率 {gm_prev:.1f}% → {gm_latest:.1f}%（{gm_momentum:+.1f}pp）"]
    if eps_yoy is not None:
        notes.append(f"EPS年增 {eps_yoy:+.1f}%")
    else:
        notes.append("EPS年增：缺去年同季資料，僅供毛利率動能參考")

    gm_rising = gm_momentum > 0
    eps_strong = eps_yoy is not None and eps_yoy >= EPS_YOY_STRONG
    eps_growing = eps_yoy is not None and eps_yoy > 0

    if gm_rising and eps_strong:
        pts = 10
    elif gm_rising or (eps_growing and eps_yoy is not None):
        pts = 6
    elif not gm_rising and eps_growing:
        pts = 4
        notes.append("營收/EPS仍成長但毛利率轉弱——獲利品質而非成長性出現警訊")
    else:
        pts = 0
    return _dim("margin_eps_trend", 10, pts, notes)


# ── Dimension 3: Guidance (0-15) — company's own Guidance, never Consensus ──
def _score_guidance(guidance_entries: List[Dict], quarterly: List[Dict], usdtwd: Optional[float],
                     actual_vs_guidance: Optional[Dict] = None) -> Dict:
    """
    benchmark_type is always "GUIDANCE" here — this dimension never mixes in
    third-party analyst Consensus, per the project owner's explicit
    data-quality mandate (Level A official Guidance vs. Level B Consensus
    must never be conflated). Three sub-scores, summing to the 15-point cap:

      (a) Guidance Revision (0-6): QoQ change in the company's OWN forward
          guidance (guidance_entries[0] vs [1]) — not vs Street, since
          Street consensus isn't reliably free — but genuinely informative
          on its own for a company that guides as consistently as TSMC.
      (b) Revenue Actual vs Guidance (0-5): beat/miss vs. the guidance the
          company gave FOR that exact quarter.
      (c) Margin Actual vs Guidance (0-4): Gross Margin + Operating Margin,
          each scored beat/in-line/miss vs. their own guided ranges.

    (b) and (c) prefer `actual_vs_guidance` (main.py's auto-fetch from
    TSMC's own IR site — both actual and guidance already in USD/%, no
    NTD/USD conversion needed) when available; this is a strictly more
    accurate source than the old fallback (FinMind's NTD actuals converted
    through a same-day USD/TWD snapshot rate, revenue-only — no gross/
    operating margin guidance comparison was possible at all before).
    """
    if not guidance_entries:
        return _dim("guidance", 15, None, ["尚無任何財測指引資料（自動抓取與人工檔案皆缺）"])

    notes = []
    pts = 0.0

    # (a) Guidance Revision — company's own QoQ outlook change.
    latest = guidance_entries[0]
    lo, hi = latest.get("revenue_guidance_low_usd_b"), latest.get("revenue_guidance_high_usd_b")
    if lo is not None and hi is not None and len(guidance_entries) >= 2:
        mid = (lo + hi) / 2
        prev = guidance_entries[1]
        plo, phi = prev.get("revenue_guidance_low_usd_b"), prev.get("revenue_guidance_high_usd_b")
        if plo is not None and phi is not None:
            pmid = (plo + phi) / 2
            qoq = (mid - pmid) / pmid * 100 if pmid else None
            if qoq is not None:
                notes.append(f"[Guidance Revision] {latest.get('quarter')}財測指引 ${lo:.1f}-{hi:.1f}B，"
                             f"較{prev.get('quarter')}指引 ${plo:.1f}-{phi:.1f}B 變動 {qoq:+.1f}%")
                if qoq >= 10:
                    pts += 6
                elif qoq >= 0:
                    pts += 4
                else:
                    notes.append("公司自身財測指引較上季下修，需留意")
    else:
        notes.append("最新一筆財測指引或前一筆比較基準缺漏，無法計算Guidance Revision")

    # (b)+(c) Actual vs Guidance — prefer the auto-fetched precise USD record.
    if actual_vs_guidance:
        arev = actual_vs_guidance.get("actual_revenue_usd_b")
        glo_r = actual_vs_guidance.get("guidance_revenue_low_usd_b")
        ghi_r = actual_vs_guidance.get("guidance_revenue_high_usd_b")
        if arev is not None and glo_r is not None and ghi_r is not None:
            gmid = (glo_r + ghi_r) / 2
            beat_pct = (arev - gmid) / gmid * 100 if gmid else None
            if beat_pct is not None:
                notes.append(f"[Actual vs Guidance] {actual_vs_guidance.get('quarter')}實際營收 ${arev:.2f}B"
                             f"（官方US$計價，非NTD換算），vs 公司自身指引中值 ${gmid:.2f}B（{beat_pct:+.1f}%）")
                if beat_pct >= 3:
                    pts += 5
                elif beat_pct >= 0:
                    pts += 3
                elif beat_pct >= -3:
                    pts += 1
                else:
                    notes.append("實際營收未達公司自身財測下緣，較大幅度的guidance miss")

        def _margin_beat(label, actual, glo, ghi):
            if actual is None or glo is None or ghi is None:
                return None, None
            if actual > ghi:
                return 2, f"{label}實際{actual:.1f}% 優於指引上緣{ghi:.1f}%（beat）"
            if actual >= glo:
                return 1, f"{label}實際{actual:.1f}% 落於指引區間{glo:.1f}%-{ghi:.1f}%（in-line）"
            return 0, f"{label}實際{actual:.1f}% 低於指引下緣{glo:.1f}%（miss）"

        gm_pts, gm_note = _margin_beat("毛利率", actual_vs_guidance.get("actual_gross_margin_pct"),
                                        actual_vs_guidance.get("guidance_gross_margin_low_pct"),
                                        actual_vs_guidance.get("guidance_gross_margin_high_pct"))
        om_pts, om_note = _margin_beat("營益率", actual_vs_guidance.get("actual_operating_margin_pct"),
                                        actual_vs_guidance.get("guidance_operating_margin_low_pct"),
                                        actual_vs_guidance.get("guidance_operating_margin_high_pct"))
        for p, n in ((gm_pts, gm_note), (om_pts, om_note)):
            if p is not None:
                pts += p
                notes.append(f"[Margin vs Guidance] {n}")
    elif quarterly and usdtwd:
        # Fallback: older FinMind-NTD + USD/TWD-snapshot approximation,
        # revenue only (no free source for GM/OM guidance in this path).
        latest_actual = quarterly[-1]
        matching_guidance = next(
            (g for g in guidance_entries if g.get("guidance_given_for_quarter_end") == latest_actual.get("date")),
            None
        )
        if matching_guidance:
            glo, ghi = matching_guidance.get("revenue_guidance_low_usd_b"), matching_guidance.get("revenue_guidance_high_usd_b")
            actual_ntd = latest_actual.get("revenue_ntd")
            if glo is not None and ghi is not None and actual_ntd:
                gmid_usd = (glo + ghi) / 2
                actual_usd_b = actual_ntd / usdtwd / 1e9
                beat_pct = (actual_usd_b - gmid_usd) / gmid_usd * 100
                notes.append(f"[Actual vs Guidance，近似值] {latest_actual['date']}季實際營收約 ${actual_usd_b:.1f}B"
                             f"（NT$換算，匯率為近期快照非當季均價，尚無自動抓取資料時的備援算法），"
                             f"vs 公司自身指引中值 ${gmid_usd:.1f}B（{beat_pct:+.1f}%）")
                if beat_pct >= 3:
                    pts += 5
                elif beat_pct >= 0:
                    pts += 3
                elif beat_pct >= -3:
                    pts += 1
                else:
                    notes.append("實際營收未達公司自身財測下緣，較大幅度的guidance miss")
        else:
            notes.append("尚無對應該季實際數字的歷史財測指引可比對beat/miss")
    else:
        notes.append("缺Actual vs Guidance比對資料（自動抓取與FinMind備援皆無）")

    return _dim("guidance", 15, pts, notes)


# ── Dimension 4: Technical Trend (0-15) — MA stack structure ────────────────
def _score_technical_trend(stock_2330: Dict) -> Dict:
    closes = [h.get("close") for h in (stock_2330.get("history") or []) if h.get("close") is not None]
    if len(closes) < 20:
        return _dim("technical_trend", 15, None, ["2330價格歷史不足20日"])

    price = closes[-1]
    ma20 = sum(closes[-20:]) / 20
    ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else None
    ma120 = sum(closes[-120:]) / 120 if len(closes) >= 120 else None

    notes = [f"價格 {price:.1f}，MA20 {ma20:.1f}"
             + (f"，MA60 {ma60:.1f}" if ma60 else "")
             + (f"，MA120 {ma120:.1f}" if ma120 else "")]

    if ma60 is not None and ma120 is not None and price > ma20 > ma60 > ma120:
        pts = 15
        notes.append("完整多頭排列：價格>MA20>MA60>MA120")
    elif ma60 is not None and price > ma20 > ma60:
        pts = 10
        notes.append("價格>MA20>MA60（MA120資料不足或排列未完整）")
    elif price > ma20:
        pts = 6
    else:
        pts = 0
        notes.append("價格跌破MA20")
    return _dim("technical_trend", 15, pts, notes)


# ── Dimension 5: Momentum composite (0-10) — KD+RSI+MACD averaged, not summed ─
def _score_momentum_composite(stock_2330: Dict) -> Dict:
    details = (stock_2330.get("score") or {}).get("details") or {}
    kd_s = (details.get("kd") or {}).get("score")
    rsi_s = (details.get("rsi") or {}).get("score")
    macd_s = (details.get("macd") or {}).get("score")
    available = [s for s in (kd_s, rsi_s, macd_s) if s is not None]
    if not available:
        return _dim("momentum_composite", 10, None, ["缺KD/RSI/MACD分數"])

    composite = sum(available) / len(available)
    pts = composite / 100 * 10
    kd_state = stock_2330.get("kd_state")
    notes = [f"KD/RSI/MACD平均分數 {composite:.0f}/100（取平均而非加總，避免三個高度相關指標重複計分）"]
    if kd_state:
        notes.append(f"KD狀態：{kd_state}")
    return _dim("momentum_composite", 10, pts, notes)


# ── Dimension 6: Relative Strength (0-10) — stock vs its benchmark index/indices ─
# Default benchmark is just TAIEX (broad market) — appropriate for a generic
# stock. TSMC additionally benchmarks against SOX/NDX (see TSMC_RS_BENCHMARKS
# below) since semiconductor-sector turns genuinely lead its price; comparing
# an insurer or food processor against SOX/NDX would be a meaningless
# benchmark, so calculate_stock_investment_score() callers for non-tech
# names should pass the default (TAIEX-only) instead.
DEFAULT_RS_BENCHMARKS = [("TAIEX", "taiex")]
TSMC_RS_BENCHMARKS = [("TAIEX", "taiex"), ("SOX", "sox"), ("NDX", "ndx")]


def _score_relative_strength(stock: Dict, macro_history: List[Dict], symbol_label: str,
                              benchmarks: Optional[List[tuple]] = None) -> Dict:
    benchmarks = benchmarks or DEFAULT_RS_BENCHMARKS
    closes = [h.get("close") for h in (stock.get("history") or []) if h.get("close") is not None]
    if len(closes) < RS_LOOKBACK_DAYS + 1:
        return _dim("relative_strength", 10, None, [f"{symbol_label}價格歷史不足"])
    stock_chg = (closes[-1] - closes[-(RS_LOOKBACK_DAYS + 1)]) / closes[-(RS_LOOKBACK_DAYS + 1)] * 100

    def index_chg(key: str) -> Optional[float]:
        vals = [h.get(key) for h in macro_history if h.get(key) is not None]
        if len(vals) < RS_LOOKBACK_DAYS + 1:
            return None
        return (vals[-1] - vals[-(RS_LOOKBACK_DAYS + 1)]) / vals[-(RS_LOOKBACK_DAYS + 1)] * 100

    rs_pairs = [(label, index_chg(key)) for label, key in benchmarks]
    rs_deltas = [(name, stock_chg - idx_chg) for name, idx_chg in rs_pairs if idx_chg is not None]
    if not rs_deltas:
        return _dim("relative_strength", 10, None, ["缺對照指數資料"])

    positive_count = sum(1 for _, d in rs_deltas if d > 0)
    avg_delta = sum(d for _, d in rs_deltas) / len(rs_deltas)
    notes = [f"{symbol_label} 近{RS_LOOKBACK_DAYS}日漲跌 {stock_chg:+.1f}%；" +
             "、".join(f"相對{n} {d:+.1f}pp" for n, d in rs_deltas)]

    if positive_count == len(rs_deltas) and avg_delta > 5:
        pts = 10
    elif positive_count >= (len(rs_deltas) + 1) // 2:
        pts = 6
    elif avg_delta > -5:
        pts = 3
    else:
        pts = 0
    return _dim("relative_strength", 10, pts, notes)


# ── Dimension 7: Institutional / Chip (0-10) — flow x price direction ──────
def _score_institutional(stock_2330: Dict) -> Dict:
    institutional = stock_2330.get("institutional") or {}
    foreign_net_3d = institutional.get("foreign_net_3d")
    closes = [h.get("close") for h in (stock_2330.get("history") or []) if h.get("close") is not None]
    if foreign_net_3d is None or len(closes) < 4:
        return _dim("institutional", 10, None, ["缺個股外資買賣超或價格歷史不足"])

    price_up = closes[-1] > closes[-4]
    foreign_buying = foreign_net_3d > INSTITUTIONAL_FLOW_THRESHOLD
    foreign_selling = foreign_net_3d < -INSTITUTIONAL_FLOW_THRESHOLD

    notes = [f"近3日累計外資 {foreign_net_3d/1000:+.0f} 張，同期股價{'上漲' if price_up else '下跌'}"]
    if price_up and foreign_buying:
        pts, tag = 10, "趨勢確認（價漲＋外資買）"
    elif not price_up and foreign_selling:
        pts, tag = 0, "空方確認（價跌＋外資賣）——非此構面之支撐訊號"
    elif price_up and foreign_net_3d < 0:
        pts, tag = 3, "背離：價漲但外資賣，須留意籌碼面未跟上"
    elif not price_up and foreign_buying:
        pts, tag = 7, "價跌但外資買，可能正在吸收賣壓（非絕對，僅供參考）"
    else:
        pts, tag = 5, "外資買賣超不明顯"
    notes.append(tag)
    return _dim("institutional", 10, pts, notes)


# ── Dimension 8: ADR Premium/Discount (0-5) ─────────────────────────────────
# Only applicable to a handful of Taiwan large-caps with an actual US ADR
# sister listing (TSMC/TSM being this project's only current example).
# has_adr=False short-circuits straight to "not applicable" for everything
# else, distinct from the ordinary "data missing" degrade path below — a
# stock with no ADR isn't a data gap, it structurally has no ADR to compare.
def _score_adr(stock: Dict, adr_stock: Optional[Dict], usdtwd: Optional[float], symbol_label: str,
                adr_ratio: float = ADR_RATIO, has_adr: bool = True) -> Dict:
    if not has_adr:
        return _dim("adr_premium", 5, None, [f"{symbol_label}無海外ADR對照掛牌，此構面不適用（非資料缺漏）"])
    if not adr_stock or not usdtwd:
        return _dim("adr_premium", 5, None, ["缺ADR價格或USD/TWD匯率"])
    adr_price = adr_stock.get("current_price")
    stock_price = stock.get("current_price")
    if not adr_price or not stock_price:
        return _dim("adr_premium", 5, None, [f"缺ADR或{symbol_label}最新價格"])

    implied = adr_price / adr_ratio * usdtwd
    premium_pct = (stock_price - implied) / implied * 100
    notes = [f"ADR ${adr_price:.1f} 換算{symbol_label}隱含價 {implied:.1f}元，{symbol_label}現價 {stock_price:.1f}元"
             f"（{'溢價' if premium_pct >= 0 else '折價'} {abs(premium_pct):.1f}%）"]

    if abs(premium_pct) < 2:
        pts = 5
    elif abs(premium_pct) < 5:
        pts = 3
    else:
        pts = 1
        notes.append("台股與ADR隱含價差偏大，可能反映短線資金流向或流動性落差，非直接看多看空訊號")
    return _dim("adr_premium", 5, pts, notes)


# ── Dimension 9: Market Regime (0-5) ────────────────────────────────────────
def _score_market_regime(regime_result: Dict) -> Dict:
    if not regime_result or not regime_result.get("available"):
        return _dim("market_regime", 5, 2.5, ["市場狀態資料不足，採中性分數"])
    regime = regime_result["regime"]
    mapping = {"BULL_TREND": 5, "RECOVERY": 5, "BULL_CORRECTION": 3, "BEAR_TREND": 1, "PANIC": 0}
    pts = mapping.get(regime, 2.5)
    notes = [f"目前市場狀態：{regime_result.get('regime_label')}"]
    return _dim("market_regime", 5, pts, notes)


# ── Dimension 10: Valuation (0-5) — trailing PER percentile ────────────────
def _score_valuation(valuation: List[Dict]) -> Dict:
    if len(valuation) < 60:
        return _dim("valuation", 5, None, ["本益比歷史不足60筆，尚無法計算百分位"])
    pers = [v["per"] for v in valuation]
    today = pers[-1]
    pct = _percentile_rank(pers, today)
    notes = [f"目前本益比 {today:.1f}，位於近{len(pers)}筆歷史資料的第 {pct:.0f} 百分位"
             "（好公司≠好價格：基本面分數再高，若估值已在自身歷史高檔，仍需留意追價風險）"]
    if pct <= VALUATION_PERCENTILE_CHEAP:
        pts = 5
    elif pct <= 50:
        pts = 4
    elif pct <= 70:
        pts = 3
    elif pct <= VALUATION_PERCENTILE_EXPENSIVE:
        pts = 2
    else:
        pts = 0
    return _dim("valuation", 5, pts, notes)


# ── Buy-point setups ─────────────────────────────────────────────────────
def _classify_buy_points(dims_by_name: Dict[str, Dict], stock: Dict, confluence_result: Optional[Dict],
                          symbol_label: str) -> List[Dict]:
    """
    Three named setups per the user's framework — deliberately more specific
    than "score is high": each combines a fundamental-quality gate with a
    market-timing trigger, so a good company at a bad price (or a falling
    knife with no fundamental support) doesn't qualify for any of them.
    """
    setups = []

    def dim_score(name):
        d = dims_by_name.get(name)
        return d["score"] if d and d.get("available") else None

    fundamentals = [dim_score("revenue_momentum"), dim_score("margin_eps_trend"), dim_score("guidance")]
    fundamentals_available = [v for v in fundamentals if v is not None]
    fundamental_sum = sum(fundamentals_available) if fundamentals_available else None
    fundamental_cap = sum(d for n, d in [("revenue_momentum", 15), ("margin_eps_trend", 10), ("guidance", 15)])

    kd_state = stock.get("kd_state")
    kd_k = stock.get("kd_k")
    tech = dim_score("technical_trend")
    volume_ratio = ((stock.get("score") or {}).get("raw") or {}).get("volume_ratio")
    foreign_net_3d = (stock.get("institutional") or {}).get("foreign_net_3d")

    # A. 基本面回撤買點 Fundamental Pullback
    if (fundamental_sum is not None and fundamental_sum >= fundamental_cap * 0.75
            and kd_k is not None and kd_k < 30 and tech is not None and tech <= 6):
        setups.append({
            "id": "fundamental_pullback",
            "label": "基本面回撤買點",
            "detail": f"基本面分數 {fundamental_sum:.0f}/{fundamental_cap} 仍強，但股價/KD顯示短線遭錯殺"
        })

    # B. 趨勢突破買點 Trend Breakout
    if (fundamental_sum is not None and fundamental_sum >= fundamental_cap * 0.6
            and tech is not None and tech >= 10
            and volume_ratio is not None and volume_ratio > 1.0
            and foreign_net_3d is not None and foreign_net_3d > 0):
        setups.append({
            "id": "trend_breakout",
            "label": "趨勢突破買點",
            "detail": "基本面與技術面同步確認：均線多頭排列＋量能放大＋外資買超"
        })

    # C. 恐慌反轉買點 Panic Reversal — explicitly reuses signal_confluence's
    # bottom conditions (B1-B3) rather than duplicating VIX/margin logic here.
    bottom_triggered = 0
    if confluence_result and confluence_result.get("available") and confluence_result.get("bottom"):
        bottom_triggered = confluence_result["bottom"].get("triggered_count", 0)
    if (fundamental_sum is not None and fundamental_sum >= fundamental_cap * 0.7
            and bottom_triggered >= 1
            and kd_state in ("OVERSOLD", "OVERSOLD_REVERSAL", "OVERSOLD_BUT_RISING")):
        setups.append({
            "id": "panic_reversal",
            "label": "恐慌反轉買點",
            "detail": f"大盤恐慌訊號共振（{bottom_triggered}項底部條件觸發）疊加{symbol_label}基本面未同步惡化"
        })

    return setups


def calculate_stock_investment_score(symbol_label: str, monthly_revenue: List[Dict],
                                      quarterly_financials: List[Dict], valuation: List[Dict],
                                      guidance_entries: List[Dict], stock: Dict, adr_stock: Optional[Dict],
                                      macro_history: List[Dict], regime_result: Optional[Dict],
                                      confluence_result: Optional[Dict], usdtwd: Optional[float],
                                      actual_vs_guidance: Optional[Dict] = None,
                                      relative_strength_benchmarks: Optional[List[tuple]] = None,
                                      has_adr: bool = False, adr_ratio: float = ADR_RATIO) -> Dict:
    """
    Compute the same 10-dimension Investment Score TSMC (2330) gets (see
    module docstring), generalized to any single tracked stock. Every
    dimension degrades independently (available=False + explanatory note)
    rather than failing the whole score when one data source is thin —
    matches this project's established convention (signal_confluence.py /
    signal_score.py) of never silently guessing.

    Two dimensions are structurally TSMC-specific and degrade to "not
    applicable" (not "data missing") for everything else unless the caller
    opts in:
      - Guidance: pass guidance_entries=[] (the normal case for a stock with
        no official-guidance data source integrated) and it shows "尚無任何
        財測指引資料", same wording as any other cold-start data gap.
      - ADR Premium/Discount: has_adr=False (the default) skips straight to
        "此構面不適用" — see _score_adr()'s docstring for why that's a
        different message than a data gap.
    relative_strength_benchmarks defaults to TAIEX-only (DEFAULT_RS_BENCHMARKS)
    — comparing a non-tech stock against SOX/NDX the way TSMC's own wrapper
    does would be a meaningless benchmark.

    actual_vs_guidance: optional, auto-fetched (main.py's
    _update_tsmc_guidance_auto, TSMC-only today) record of the realized
    actual vs. the guidance given for that same quarter — see
    _score_guidance()'s docstring.
    """
    dims = [
        _score_revenue_momentum(monthly_revenue),
        _score_margin_eps(quarterly_financials),
        _score_guidance(guidance_entries, quarterly_financials, usdtwd, actual_vs_guidance),
        _score_technical_trend(stock),
        _score_momentum_composite(stock),
        _score_relative_strength(stock, macro_history, symbol_label, relative_strength_benchmarks),
        _score_institutional(stock),
        _score_adr(stock, adr_stock, usdtwd, symbol_label, adr_ratio, has_adr),
        _score_market_regime(regime_result),
        _score_valuation(valuation),
    ]
    dims_by_name = {d["name"]: d for d in dims}

    scored = [d["score"] for d in dims if d["available"]]
    total = round(sum(scored), 1) if scored else None
    coverage = f"{len(scored)}/{len(dims)}"

    buy_points = _classify_buy_points(dims_by_name, stock, confluence_result, symbol_label)

    return {
        "available": total is not None,
        "total": total,
        "coverage": coverage,
        "recommendation": _recommendation(total) if total is not None else None,
        "dimensions": dims,
        "buy_points": buy_points,
        "caveat": ("本分數為規則式加權評分，且法說會財測指引為人工維護資料（非分析師市場共識），"
                   "尚未經歷史回測驗證統計勝率，僅供比較「目前有多少項已知條件成立」，並非機率或投資建議。"),
    }


def calculate_tsmc_score(monthly_revenue: List[Dict], quarterly_financials: List[Dict],
                          valuation: List[Dict], guidance_entries: List[Dict],
                          stock_2330: Dict, stock_tsm: Optional[Dict],
                          macro_history: List[Dict], regime_result: Optional[Dict],
                          confluence_result: Optional[Dict], usdtwd: Optional[float],
                          actual_vs_guidance: Optional[Dict] = None) -> Dict:
    """
    TSMC (2330)'s own thin wrapper around calculate_stock_investment_score()
    — kept as a separate entry point (rather than inlining these arguments
    at every call site) since 2330 is the only tracked stock with a real ADR
    sister listing and a genuine semiconductor-cycle rationale for
    benchmarking against SOX/NDX in addition to TAIEX (see module docstring).
    """
    return calculate_stock_investment_score(
        "2330", monthly_revenue, quarterly_financials, valuation, guidance_entries, stock_2330, stock_tsm,
        macro_history, regime_result, confluence_result, usdtwd, actual_vs_guidance=actual_vs_guidance,
        relative_strength_benchmarks=TSMC_RS_BENCHMARKS, has_adr=True, adr_ratio=ADR_RATIO,
    )


# ── Fundamentals Summary — quarterly highlights / news / valuation / bull-bear ─
#
# A separate, human-readable companion to calculate_tsmc_score() above: that
# function produces a 100-point rule-based score for internal comparison
# across time; this one answers four concrete questions a reader actually
# asks about 2330 ("this quarter's numbers vs last year", "what's in the
# news", "is it cheap or expensive right now", "what's the bull/bear case").
#
# The bull/bear points are NOT a separate judgment call or LLM summary —
# deliberately, to stay consistent with this project's no-guessing rule-based
# philosophy (see module docstring). They're derived mechanically from the
# SAME 10 dimensions calculate_tsmc_score() already computed: the top-3
# highest-scoring (as a fraction of each dimension's cap) become 利多, the
# bottom-3 become 利空, reusing each dimension's own first note as the
# bullet text. Two dimensions are excluded from this ranking on purpose —
# market_regime (a macro context modifier, not evidence about 2330 itself)
# and adr_premium (its own scoring note explicitly says a large ADR/local
# price gap "非直接看多看空訊號" / is not a directional signal) — including
# either would risk mislabeling a neutral reading as a bull or bear point.
_BULL_BEAR_ELIGIBLE_DIMS = {
    "revenue_momentum", "margin_eps_trend", "guidance", "technical_trend",
    "momentum_composite", "relative_strength", "institutional", "valuation",
}

NEWS_CAVEAT = ("新聞為即時網頁擷取之標題列表（Yahoo奇摩股市個股新聞頁），並非法說會逐字稿或內容摘要；"
               "頁面本身不保證僅涵蓋近一個月或提供可靠發布日期，僅供快速瀏覽近期話題，詳細內容請點閱原文查證。")


def _quarter_label(date_str: str) -> str:
    year, month = int(date_str[:4]), int(date_str[5:7])
    quarter = {3: 1, 6: 2, 9: 3, 12: 4}.get(month)
    return f"{year}Q{quarter}" if quarter else date_str


def _gross_margin_pct(q: Dict) -> Optional[float]:
    revenue, gross_profit = q.get("revenue_ntd"), q.get("gross_profit_ntd")
    return (gross_profit / revenue * 100) if revenue and gross_profit is not None else None


def _quarterly_highlights(quarterly: List[Dict]) -> Dict:
    """
    近一季財報重點：營收、毛利率、EPS，與去年同期比較。Reuses the same
    year/month-matched YoY lookup as _score_margin_eps() above (kept
    separate rather than sharing code — that function only needs the
    single-quarter momentum delta, this needs the full YoY comparison set).
    """
    if not quarterly:
        return {"available": False, "reason": "缺季度財報資料（FinMind尚未有資料或抓取失敗）"}

    latest = quarterly[-1]
    yoy_match = next(
        (q for q in quarterly
         if q["date"][:4] == str(int(latest["date"][:4]) - 1) and q["date"][5:7] == latest["date"][5:7]),
        None
    )

    revenue, eps = latest.get("revenue_ntd"), latest.get("eps")
    gross_margin = _gross_margin_pct(latest)
    revenue_yoy_pct = gross_margin_yoy_pp = eps_yoy_pct = None
    if yoy_match:
        prev_revenue = yoy_match.get("revenue_ntd")
        if revenue is not None and prev_revenue:
            revenue_yoy_pct = (revenue - prev_revenue) / prev_revenue * 100
        prev_gross_margin = _gross_margin_pct(yoy_match)
        if gross_margin is not None and prev_gross_margin is not None:
            gross_margin_yoy_pp = gross_margin - prev_gross_margin
        prev_eps = yoy_match.get("eps")
        if eps is not None and prev_eps:
            eps_yoy_pct = (eps - prev_eps) / abs(prev_eps) * 100

    return {
        "available": True,
        "quarter": _quarter_label(latest["date"]),
        "yoy_quarter": _quarter_label(yoy_match["date"]) if yoy_match else None,
        "revenue_ntd": revenue,
        "revenue_yoy_pct": round(revenue_yoy_pct, 1) if revenue_yoy_pct is not None else None,
        "gross_margin_pct": round(gross_margin, 1) if gross_margin is not None else None,
        "gross_margin_yoy_pp": round(gross_margin_yoy_pp, 1) if gross_margin_yoy_pp is not None else None,
        "eps": eps,
        "eps_yoy_pct": round(eps_yoy_pct, 1) if eps_yoy_pct is not None else None,
    }


def _valuation_summary(stock_2330: Optional[Dict], valuation: List[Dict], peer_valuation: List[Dict]) -> Dict:
    """目前股價、本益比，和同業比較（見 fetcher.TSMC_PEER_SYMBOLS 的同業選取說明）。"""
    current_price = (stock_2330 or {}).get("current_price")
    latest_per = valuation[-1]["per"] if valuation else None
    peers = [p for p in (peer_valuation or []) if p.get("per") is not None]
    peer_avg_per = sum(p["per"] for p in peers) / len(peers) if peers else None
    vs_peer_avg_pct = ((latest_per - peer_avg_per) / peer_avg_per * 100
                        if latest_per is not None and peer_avg_per else None)
    return {
        "available": current_price is not None or latest_per is not None,
        "current_price": current_price,
        "per": latest_per,
        "peers": [{"symbol": p["symbol"], "name": p["name"], "per": p["per"]} for p in peers],
        "peer_avg_per": round(peer_avg_per, 1) if peer_avg_per is not None else None,
        "vs_peer_avg_pct": round(vs_peer_avg_pct, 1) if vs_peer_avg_pct is not None else None,
    }


def _bull_bear_points(dimensions: List[Dict], top_n: int = 3) -> Dict:
    eligible = [d for d in dimensions
                if d.get("available") and d.get("cap") and d["name"] in _BULL_BEAR_ELIGIBLE_DIMS]
    ranked = sorted(eligible, key=lambda d: d["score"] / d["cap"])

    def _point(d: Dict) -> Dict:
        return {"dimension": d["name"], "score": d["score"], "cap": d["cap"],
                "detail": d["notes"][0] if d.get("notes") else None}

    bear = [_point(d) for d in ranked[:top_n]]
    bull = [_point(d) for d in reversed(ranked[-top_n:])] if ranked else []
    return {"bull_points": bull, "bear_points": bear}


def build_fundamentals_summary(quarterly_financials: List[Dict], valuation: List[Dict],
                                peer_valuation: List[Dict], stock_2330: Optional[Dict],
                                news_items: List[Dict], tsmc_analysis: Optional[Dict]) -> Dict:
    """
    2330 基本面摘要卡：近一季財報重點 / 近期新聞 / 股價與本益比同業比較 / 利多利空各三點。

    Deliberately takes the already-computed `tsmc_analysis` (calculate_tsmc_score()'s
    return value) rather than recomputing its own scoring pass — bull/bear
    points must always be read off the SAME dimension scores shown elsewhere
    on the dashboard, never a second independently-derived number that could
    silently drift out of sync with them.
    """
    dims = (tsmc_analysis or {}).get("dimensions") or []
    return {
        "available": True,
        "quarterly_highlights": _quarterly_highlights(quarterly_financials),
        "news": (news_items or [])[:8],
        "news_caveat": NEWS_CAVEAT,
        "valuation": _valuation_summary(stock_2330, valuation, peer_valuation),
        **_bull_bear_points(dims),
    }
