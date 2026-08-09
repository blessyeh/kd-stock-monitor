# 📊 KD Stock Monitor | 股票 KD 指標監控系統

[English](#english) | [繁體中文](#繁體中文)

---

<a name="english"></a>
## 🌐 English Description

A GitHub-powered stock monitoring system that tracks KD (Stochastic Oscillator) indicators for Taiwan and US stocks. Features automatic **hourly** data updates and a web dashboard deployed on GitHub Pages.

### ✨ Features
- 📈 **KD Indicator Tracking**: Calculates 9-day Stochastic Oscillator (KD) for all monitored stocks.
- 🔔 **Smart Alerts**: Automatic notifications when KD ≥ 80 (overbought) or ≤ 20 (oversold), tagged with a MA/Bollinger/MACD filter-confidence check to flag likely indicator failure (see below).
- 🇹🇼 **Taiwan Stocks**: Supports TWSE stocks (e.g., 0050.TW, 2330.TW).
- 🇺🇸 **US Stocks**: Supports NYSE/NASDAQ stocks (e.g., AAPL, TSLA).
- 🌐 **Web Dashboard**: Interactive dashboard with charts and real-time data. TAIEX (台股加權指數) and the TAIFEX night-session gap are shown prominently at the top of the page, above everything else.
- 🌍 **Global Macro Indicators**: VIX, US 10Y yield, DXY, Bitcoin, WTI Crude Oil, Gold, plus SOX (Philadelphia Semiconductor), Nasdaq 100, and S&P 500 — the indices that actually drive TW-listed tech/semiconductor names, rather than the Dow.
- 🇹🇼 **Taiwan Chip Flow**: Foreign/investment-trust net buy-sell, margin & short balances, USD/TWD (TWSE open data), foreign TAIFEX futures net position and options Put/Call Ratio (FinMind), plus a retrospective TAIFEX night-session (夜盤) gap indicator.
- 🎯 **Signal Confluence Model**: Cross-validates macro + chip-flow + derivatives + tech-index indicators against a fully-verified top/bottom turning-point framework (see below).
- ⚡ **Auto Updates**: **Hourly** automated data fetching and deployment via GitHub Actions.
- 📱 **Mobile Friendly**: Responsive design works on all devices.

### 📉 Trading Patterns
Automated analysis of 11 market patterns:
1. 🔴 **Quick Rise, Slow Fall** (Main force shipping): Usually a sell signal.
2. 🟢 **Quick Fall, Slow Rise** (Main force accumulating): Usually a buy signal.
3. 🔴 **Volume Surge on Rise** (Peak risk): Potential top forming, suggest sell.
4. ⚫ **Shrinking Volume, No Fall** (Top forming): Suggest avoid.
5. 🟡 **Shrinking Volume on Rise** (Healthy trend): Trend is healthy, suggest hold.
6. ⚫ **Shrinking Volume on Fall** (Continued bearish): Lack of buying power.
7. 🔴 **Shrinking Volume, No Rise** (Top confirmed): Suggest sell.
8. 🟢 **Volume Surge on Fall** (Panic selling): Potential buying opportunity.
9. 🟢 **Panic Bottom** (Short-term rebound): Extremely strict signal, only a few times per year.
10. 🔴 **Blowoff Top** (Inevitable pullback): Extremely strict signal, extreme short-term overheating.
11. 🟢 **Chip Lock Rally** (Main uptrend continuation): Extremely strict signal, highly concentrated chips in a strong uptrend.

### 🛡️ KD Alert Filters (indicator-failure guard)
KD is a bounded oscillator — it assumes price mean-reverts inside a range. In a strong trend it "sticks" at an extreme for weeks (鈍化 / indicator failure): a raw `KD ≥ 80` check alone would fire non-stop through a genuine breakout rally (tempting an early sell that misses the whole move), and a raw `KD ≤ 20` check alone can't tell a real bounce setup from a stock that's simply still falling. Every KD extreme still generates an alert (nothing is hidden), but each one is now run through the same MA / volume / MACD / Bollinger Band data the multi-dimensional scoring engine already computes, and tagged with a confidence level:
- **高信心 High confidence**: for oversold, price sits above a rising 20-day MA (a pullback inside an uptrend) and/or price has touched the lower Bollinger Band, with MACD not accelerating downward. For overbought, price is *not* holding above a rising 20-day MA, or price is stretched to the upper Bollinger Band without volume confirmation (exhaustion, not fresh strength).
- **疑似鈍化 Likely indicator failure**: for oversold, price is below/under a falling 20-day MA (real downtrend, no MA/Bollinger support) or MACD is still accelerating down. For overbought, price is still comfortably above a rising 20-day MA with MACD still accelerating up (classic runaway-rally 鈍化, not a top).
- **資料不足 Unknown**: fewer than ~25 trading days of history (new tickers), so the filters can't run yet — the raw KD alert still fires, just unlabeled.

The concrete filter reasons (which checks passed vs. flagged caution) are shown directly on each alert card in the dashboard. Each alert (and each stock card) now also carries a **KD State** (see next section) and, once enough history exists, a **Market Regime** tag — see "Market Regime & Signal Score" further below for how regime shifts this confirmation bar.

### 🔬 KD Engine & Data-Integrity Fixes (2026-08-09)
A code-level review of `src/kd_calculator.py` and `src/signal_confluence.py` surfaced several correctness issues worth fixing before adding anything new — summarized here since they change what the existing numbers mean, not just how they're displayed.

- **RSV zero-range handling made explicit**: RSV (`100 * (Close - LowestLow) / (HighestHigh - LowestLow)`) divides by zero when price hasn't moved at all within the lookback window (a halted or extremely illiquid ticker). This previously landed on the same neutral 50 value via a blanket `.fillna(50)` after the division — correct by coincidence, but conflating "range is genuinely flat, 50 is RSV's own defined value here" with "this row broke for an unrelated reason". Now computed explicitly: every row defaults to 50, and only rows with a non-zero range get the real division result.
- **KD initialization convention documented**: the first `k_period - 1` rows (default 9-day setting → first 8 rows) get a flat K=D=50 rather than participating in the recursive formula with a partial lookback window — this was already the code's behavior, just not stated anywhere. Worth knowing if comparing against another charting platform, since some seed K/D differently (e.g. K/D = RSV on day 1) and will disagree for the first several rows of any series.
- **KD State replaces the old flat overbought/oversold/bullish/bearish/neutral read** (`KDCalculator.analyze_kd_signal()`). The previous version's docstring promised `golden_cross`/`death_cross` as possible outputs but the function never actually detected a crossover — a real docstring/implementation mismatch. Now classifies into 10 states using today's *and* yesterday's K/D (crossover direction, and whether the K-D gap is widening or narrowing): `GOLDEN_CROSS`, `DEATH_CROSS`, `OVERBOUGHT_BUT_RISING` (gap still widening — momentum intact, likely 鈍化 rather than a top), `OVERBOUGHT_REVERSAL` (gap narrowing — more likely a genuine top), `OVERBOUGHT`, `OVERSOLD_REVERSAL` (gap narrowing, K climbing back toward D — the clearest pre-golden-cross bottoming read), `OVERSOLD_BUT_RISING`, `OVERSOLD`, `BULLISH_MOMENTUM`, `BEARISH_MOMENTUM`. This directly answers a real gap in the old classifier: K=95/D=80 (gap wide, likely still building) and K=95/D=94 (gap almost closed, likely stalling) used to both just read "overbought" — now they don't. Computed per stock in `calculate_all_stocks()`, stored as `kd_state`, and shown on every stock card and alert.
- **Date-alignment bug in lookback/streak calculations, fixed across `signal_confluence.py`, `signal_score.py`, and `market_regime.py`**: all three previously extracted a field's history via a helper that dropped any day where that field was `None` *before* taking the last N values — so a single missing day silently shifted what "3 consecutive days", "5-day change", or "200-day moving average" actually measured, without any error or warning. Example: raw data `8/1 -100, 8/2 None, 8/3 -200, 8/4 -300` compacted to `[-100, -200, -300]`, so a "3 consecutive sell days" check would compare 8/1 vs 8/4 as if they were 3 trading days apart, not 4. Fixed by switching every lookback/streak/moving-average calculation to `_window()` / `_lookback()` (in `signal_confluence.py`, imported by the other two modules), which require an exact, gap-free calendar window and report "insufficient data" if even one day inside that window is missing, rather than silently reaching further back to compensate. The one deliberate exception is signal_score.py's VIX percentile-rank (Sentiment dimension) — a distributional statistic that doesn't depend on values being calendar-consecutive, so it keeps a documented gap-tolerant collector (`_recent_values()`) instead.
- **T2's "TWD breaks a round-number level" condition** (`int(today) > int(prior)`) is mathematically equivalent to `floor()` for positive exchange-rate values, so it wasn't actually miscalculating — but the round-number step size (NT$1) was an unstated side effect of using `int()` rather than a real, documented, tunable parameter. Replaced with an explicit `floor(value / step)` comparison against a new `TWD_ROUND_NUMBER_STEP` constant.

### 📊 Per-Stock Institutional Flow (個股外資買賣超)
Beyond the market-wide foreign/investment-trust net buy-sell already covered in Taiwan Chip Flow Indicators (below), each individually-tracked TW ticker now gets its own foreign/investment-trust/dealer net buy-sell in shares, via FinMind's `TaiwanStockInstitutionalInvestorsBuySell` dataset (works uniformly for TWSE, TPEx/OTC, and ETFs). This feeds directly into the KD Alert Filters above as an additional confirming signal: a 3-day cumulative foreign net buy during an oversold reading, or a 3-day cumulative foreign net sell during an overbought reading, can independently confirm the alert even when the MA/Bollinger filters don't — smart-money accumulation/distribution in a specific stock is a real signal on its own, not just a byproduct of price action. Shown on every TW stock card in the dashboard.

### 🔒 Manage Watchlist (owner-only add/remove)
The dashboard has a "管理監控股票" panel for adding or removing a monitored stock — restricted to the repo owner, with **no credentials of any kind stored in or entered into the site**. Submitting the form opens a pre-filled GitHub "New Issue" (`[監控股票申請] ...`) instead of calling any API directly. A dedicated workflow (`.github/workflows/stock-request.yml`) is the actual gatekeeper: it only ever runs for issues opened by `github.repository_owner` — a request opened by anyone else is left completely untouched (no comment, no config change). When it does run, it parses the issue body, updates `config.json` via `scripts/apply_stock_request.py`, commits, and comments + closes the issue with the result; the push then triggers the normal hourly update workflow to fetch the new/removed ticker within minutes. This design deliberately avoids storing a GitHub token in the browser — an earlier PAT-in-`localStorage` version of this idea was removed for exactly that risk (see commit `53fc74560`).

### 📰 Major Financial News (重大財經新聞)
A "重大財經新聞" panel shows the latest macro/market headlines, scraped hourly from **Yahoo奇摩股市** (`tw.stock.yahoo.com/news`) — a genuinely separate, natively Traditional Chinese news operation from Yahoo, not a machine translation of the English `finance.yahoo.com` site. Its 財經新聞 section covers Fed/macro, US markets, HK/China markets, gold, and FX, plus Taiwan-specific market news the English site doesn't have, so switching sources gave native Chinese content *and* better coverage in one move, without adding a translation step (extra API dependency, cost, and translation-quality risk). This is deliberately the most fragile data source in the whole pipeline, by necessity rather than choice: Yahoo doesn't offer a working public news feed anymore as of 2026 — both `yfinance`'s own news lookup and Yahoo's legacy RSS feed (`feeds.finance.yahoo.com/rss/2.0/headline`) returned empty/blocked responses when tested, leaving direct page scraping as the only option that actually returns content. `fetcher.py`'s `fetch_market_news()` parses by **URL pattern** (every Yahoo Finance/Yahoo奇摩股市 article URL ends in `-<6+ digit ID>.html`) rather than CSS class names, since URL structure tends to survive page redesigns that break styling-based selectors — but it can still legitimately return nothing if Yahoo changes their markup entirely or blocks the request from GitHub Actions' IP range. This always fails silently (empty list, logged warning) and never breaks the rest of the pipeline; the dashboard just shows "暫無新聞" when that happens.

### 🇹🇼 TAIEX (台股大盤/加權指數)
Shown prominently at the very top of the dashboard, above everything else — it's the actual index this whole project exists to monitor, not just another supporting macro indicator. Right beside it is the TAIFEX night-session (夜盤) gap (see Taiwan Chip Flow Indicators, item 6 below) — paired together since the night session is the overnight lead-in to TAIEX's next open.
在儀表板最上方最顯眼的位置顯示——這是本專案真正要監控的指數本體，不只是眾多輔助宏觀指標之一。旁邊搭配顯示台指期夜盤跳空（見下方台股籌碼面指標項目 6）——兩者放在一起，因為夜盤正是 TAIEX 下一個開盤的隔夜前哨。

### 🌐 Macro Indicators | 宏觀指標
1. **VIX (Fear Index) | VIX 恐慌指數**: Measures market volatility and fear levels. High VIX (>30) indicates high fear and potential buying opportunities.
   *   衡量市場波動度與恐慌情緒。高 VIX (>30) 通常代表恐慌，可能是分批買點。
2. **US 10Y (Bond Yield) | 美債 10 年期收益率**: Benchmark for risk-free rates. Rising yields can put pressure on stock valuations, especially for tech stocks.
   *   無風險利率的基準。收益率上升會對股市估值造成壓力，尤其是科技股。
3. **DXY (US Dollar Index) | 美元指數**: Strength of the USD. Strong dollar often correlates with pressure on emerging markets and commodity prices.
   *   衡量美元強度。強勢美元通常會對新興市場與大宗商品價格產生壓力。
4. **BTC (Bitcoin) | 比特幣**: Often considered a high-risk asset proxy. Its trend can reflect overall market risk appetite.
   *   通常被視為高風險資產的代表。其趨勢反映了市場對風險的整體偏好程度。
5. **WTI Crude Oil | 原油 (WTI)**: A proxy for input-cost inflation. Rising oil prices can squeeze corporate margins and keep central banks hawkish.
   *   生產與運輸成本的代表。油價飆升會引發輸入型通膨，壓抑企業利潤，並迫使央行維持高利率。
6. **Gold | 黃金**: A hedge against geopolitical risk and currency debasement, complementing Bitcoin as an alternative "risk appetite" read.
   *   對沖地緣政治風險與法幣貶值的工具，可與比特幣（高風險偏好）互補觀察市場情緒。
7. **SOX (Philadelphia Semiconductor Index) | 費城半導體指數**: TWSE's weighted index is effectively a tech/semiconductor-heavy index — TSMC and its supply chain dominate its weighting — so SOX's turning points are a leading "source pricing" signal for TW's, with far more predictive power than the Dow (traditional blue-chip industrials, weak correlation with TW earnings/flows).
   *   台股加權指數本質上是「科技/半導體重壓指數」（台積電及其供應鏈佔絕對權重），SOX 的轉折是台股轉折的「源頭定價」訊號，預測力遠高於道瓊（傳統藍籌工業股，與台股獲利/資金連動性極低）。
8. **Nasdaq 100 (NDX) | 那斯達克100指數**: Covers the world's major tech giants (Apple, NVIDIA, etc.) — the end customers that place the orders driving TW's electronics supply chain.
   *   涵蓋全球主要科技巨頭（如 Apple、NVIDIA），這些公司是台股電子供應鏈訂單的終端大客戶。
9. **S&P 500 | 標普500指數**: The standard read on overall US macro health, used to judge whether the US is heading into recession.
   *   反映美國整體總體經濟狀況的標準指標，用於判斷美國是否步入衰退。

### 🇹🇼 Taiwan Chip Flow Indicators | 台股籌碼面指標
Items 1–3 are sourced from TWSE's official free open-data endpoints (no API key required); items 4–6 are sourced from FinMind's open-data API (`api.finmindtrade.com`, free tier, no key required — an optional `FINMIND_TOKEN` env var raises the rate limit). All are End-of-Day figures — posted after market close — not intraday ticks, so the dashboard shows which trading day each value is actually for.
項目 1–3 來自台灣證交所 (TWSE) 官方免費開放資料 (無需 API 金鑰)；項目 4–6 來自 FinMind 開放資料 API (`api.finmindtrade.com`，免費額度、無需金鑰，可選填 `FINMIND_TOKEN` 環境變數以提高流量上限)。這些皆為每日收盤後才會公布的資料，並非即時報價，因此儀表板會標示每個數值實際對應的交易日。

1. **Foreign / Investment Trust Net Buy-Sell | 外資 / 投信買賣超**: Market-wide net NT$ flow from the daily 三大法人買賣金額統計表 (BFI82U). Foreign investors dominate TWSE market cap, so sustained buying/selling drives the index's medium-term direction; 投信 flows matter most for small/mid caps and ETF constituents.
   *   來自「三大法人買賣金額統計表」的全市場淨買賣金額。外資占台股市值比重極高，是加權指數中長期方向的主要驅動力；投信資金對中小型股與 ETF 成分股影響力較大。
2. **Margin / Short Balance & Ratio | 融資融券餘額與資券比**: From the daily 信用交易統計 (MI_MARGN). Margin balance reflects retail leverage; short balance reflects bearish bets. A sudden, sharp drop in margin balance ("融資斷頭") is one of the most objective signs of forced retail capitulation.
   *   來自「信用交易統計」。融資餘額代表散戶槓桿多頭力道，融券餘額代表空頭部位。融資餘額單日大減（俗稱「融資斷頭」）是散戶籌碼洗淨最客觀的訊號之一。
3. **USD/TWD Exchange Rate | 新台幣匯率**: A leading/coincident indicator for foreign capital flows — TWD appreciation typically accompanies foreign inflows, sustained depreciation typically accompanies foreign capital leaving.
   *   外資進出台股的領先/同步指標。新台幣升值通常伴隨外資匯入，持續貶值則通常伴隨外資撤出。
4. **Foreign TAIFEX Futures Net Position | 外資台指期未平倉淨部位**: Net long/short open interest held by foreign institutional investors in TAIFEX index futures (`TaiwanFuturesInstitutionalInvestors` dataset). A heavy net-short position alongside spot selling signals foreign investors are hedging or betting on further downside, not just trimming spot holdings.
   *   外資在台指期的多空未平倉淨部位（`TaiwanFuturesInstitutionalInvestors` 資料集）。若現貨賣超同時期貨呈現大量淨空單，代表外資不只是調節現貨，而是在避險或看空後市。
5. **Options Put/Call Ratio | 選擇權 Put/Call Ratio**: Open-interest ratio of TXO put options to call options (`TaiwanOptionDaily` dataset). A low ratio (crowded call side) signals complacency near market tops; a rising ratio signals fear/hedging demand.
   *   台指選擇權 (TXO) put/call 未平倉量比（`TaiwanOptionDaily` 資料集）。比值偏低代表市場偏多、樂觀情緒濃厚，接近頭部風險；比值走高則代表避險/恐慌需求上升。
6. **TAIFEX Night-Session Gap | 台指期夜盤跳空**: Front-month TX futures close during the after-hours session (15:00–05:00 Taipei) vs. the prior day session's close (`TaiwanFuturesDaily`, `trading_session=after_market`). This is a **retrospective** confirmation of what already happened overnight — FinMind only publishes the full day's data (both sessions) in its ~16:30 Taipei daily batch, same cadence as items 1–5. It is *not* a live intraday feed you could act on during the actual night session; that would require FinMind's paid sponsor-tier real-time snapshot endpoint, which this project doesn't use.
   *   近月台指期夜盤（台北時間 15:00–05:00）收盤價 vs. 前一交易日盤收（`TaiwanFuturesDaily`，`trading_session=after_market`）。這是**追溯性**資料，用來確認「昨夜已經發生的事」——FinMind 只在約台北時間 16:30 的每日批次中一次公布完整的日盤+夜盤資料，與項目 1–5 同一節奏。這**不是**能在夜盤當下即時操作的盤中報價；真正即時的資料需要 FinMind 付費 sponsor 方案的即時快照端點，本專案並未使用。

### 🎯 Signal Confluence Model | 訊號共振：大盤轉折模型
No single macro or chip indicator is trusted in isolation — this model (`src/signal_confluence.py`) only flags a potential turning point when **multiple independent conditions agree**, cross-validating global macro flows, TWD, and TW-specific chip flow.
不單看任何單一指標——這個模型（`src/signal_confluence.py`）只有在**多項獨立條件同時出現共振**時才會標示可能的轉折點，交叉驗證全球宏觀資金、匯率與台股籌碼面。

**Top structure / hedge-trigger signals | 頂部結構與避險啟動訊號** (risk rising):
- Macro capital drain: DXY breaks above its recent high **and** US 10Y yield rises quickly. | 宏觀資金抽離：DXY 突破前高，且美債 10Y 快速攀升。
- TWD depreciation: sustained weakening or breaking a round-number level. | 匯率表態：新台幣連續走貶或貶破整數關卡。
- Foreign spot+futures dual short: sustained spot selling **and** a heavy net-short TAIFEX futures position. | 外資期現貨雙空：現貨連續賣超，且台指期淨部位達重度空單門檻。
- Retail holding the bag: foreign selling while margin balance keeps rising **and** the options Put/Call Ratio is low (complacent). | 籌碼過度樂觀/散戶接刀：外資倒貨同時融資餘額不退，且選擇權 P/C Ratio 偏低（市場過度樂觀）。
- Tech capital retreat: SOX and/or Nasdaq 100 breaks below its recent-day support **and** US 10Y yield rises quickly — the "source pricing" mechanism, since TWSE's index is effectively tech/semiconductor-weighted. | 科技資金退潮：費半 (SOX) 或那斯達克100 (NDX) 跌破近期支撐，且美債 10Y 快速攀升——「源頭定價」機制，因台股加權指數本質上是科技/半導體重壓指數。

**Bottom turning point / add-position signals | 底部轉折與加碼訊號** (crisis clearing):
- VIX extreme reversal: spikes above 30 then rolls over. | 恐慌極值反轉：VIX 飆高後見頂回落。
- Retail capitulation: a sharp single-day drop in margin balance ("融資斷頭"). | 散戶投降：融資餘額斷頭式大減。
- FX stabilizing + foreign spot flow reversal **and** TAIFEX futures short-covering. | 匯率止穩、外資現貨轉買，且台指期空單回補中。

All conditions above are now fully verifiable — the TAIFEX futures net position and options Put/Call Ratio are fetched via FinMind (see Taiwan Chip Flow Indicators, items 4–5). Each condition still reports itself as unavailable (rather than a false trigger) until enough daily history (`data/macro_history.json`) has accumulated. The panel itself only turns on after **21 trading days** (~1 month) — chosen to match the longest individual condition window (T1's DXY breakout and T5's SOX/NDX support breakdown both need a 20-day lookback plus today), so that once the panel says "available," every condition can actually evaluate rather than a few staying stuck at "insufficient data" for weeks after the panel already claims to be live.

You don't have to wait three weeks of hourly runs for that history to build up, though: the first run where history is still short automatically does a **one-time historical backfill** (`fetcher.backfill_macro_history()`) — a single `yfinance` call per ticker and a single date-range call per FinMind dataset already return weeks of history in one shot; only the TWSE chip-flow figures (foreign/investment-trust net buy-sell, margin balance) need a per-day loop, since TWSE's free reports don't support range queries. That loop is the slow part (up to ~70 sequential requests, a couple of minutes, with a small delay between calls to be polite to a free public endpoint) but only runs once — a marker file (`data/.macro_backfill_done`) prevents it from re-running every hour even if it only partially succeeds. Delete that marker file to force a retry. The backfill only fills gaps; it never overwrites a value a normal run has already recorded.

The TAIFEX night-session gap (item 6) is shown on the dashboard as supporting context — how large last night's overnight move was — but isn't wired into a signal-confluence condition itself, since it's retrospective (not available until well after the day session has already opened and reacted to it).
夜盤跳空（項目 6）在儀表板上作為輔助參考顯示——呈現昨夜跳空的幅度——但並未納入訊號共振的條件判斷，因為這是追溯性資料（要到日盤已經開盤反應過後才能取得）。
以上所有條件現在皆可完整驗證——台指期淨部位與選擇權 P/C Ratio 已透過 FinMind 取得（見台股籌碼面指標項目 4–5）。在每日歷史資料（`data/macro_history.json`）累積足夠天數之前，各條件會回報「資料不足」而非誤判觸發。

⚠️ Per the model's own design intent: this is a reference point for large lump-sum entries or pausing a chase-the-rally purchase — **not** a signal for frequent trading or shorting. If you're running a DCA strategy on a broad-market ETF (e.g., 0050), letting short-term futures/chip noise trigger "dynamic hedging" typically costs more (in hedging losses when the read turns out wrong) than it saves.
⚠️ 依照模型本身的設計初衷：這是單筆大額加碼或停止追高的參考依據，**並非**頻繁進出或放空訊號。若本身在對大盤型 ETF（如 0050）執行定期定額策略，讓短線期貨/籌碼雜訊觸發「動態避險」，一旦判斷錯誤，避險成本通常比它省下的還多。

### 🧭 Market Regime & Signal Score
The project's threshold-based conditions (T1–T5 / B1–B3 above, and the per-stock KD filters) are all still hand-tuned rules — turning several rules into "N conditions triggered" doesn't by itself make the result a validated statistical edge. This pair of modules is a first step toward a more rigorous framework, addressing two specific gaps: **the same raw reading means different things in different market backdrops**, and **a boolean "N/5 triggered" hides how strong or weak the case actually is**.

- **Market Regime** (`src/market_regime.py`) classifies the current backdrop into one of five states from `data/macro_history.json`: **Bull Trend** (TAIEX above its long moving average, average still rising), **Bull Correction** (still above the average, but it's flattened/turned down), **Bear Trend** (below the average, no stabilizing signal), **Panic** (VIX spiking fast and already elevated — acute stress regardless of trend position), **Recovery** (VIX rolling over from a recent peak *and* foreign capital flow reversing from net-sell to net-buy — a transitional state coming out of stress). The moving-average period is adaptive (200/120/60/20-day ladder, longest the accumulated history can support) rather than hard-coded to 200 days, since `backfill_macro_history()` only seeds ~35 days on first run and it takes months to reach a full 200-day window — the dashboard always shows which period was actually used.
  This regime label feeds directly into the per-stock KD alert filters (`alert_checker.py`'s `_evaluate_filters`): the same KD≤20 reading gets its confirmation bar **lowered** in a Bull Correction or Recovery backdrop ("buy the dip" context) and **raised** in a Bear Trend or Panic backdrop (falling-knife risk), rather than being evaluated the same way regardless of what the broader market is doing. Every alert now also carries `market_regime` / `market_regime_label` so the dashboard can show exactly which backdrop shaped that particular confirmation call.

- **Signal Score** (`src/signal_score.py`) re-expresses the same underlying data used by Signal Confluence as two 0-100 scores — **Top Risk Score** and **Bottom Setup Score** — each split into five weighted dimensions: Macro (0-25), Chip Flow (0-25), Derivative (0-20), Technical (0-20, computed directly on TAIEX's own closes via a 20-day Bollinger band + RSI(14) rather than any individual stock), and Sentiment (0-10, a VIX percentile-rank within its own trailing window rather than a fixed threshold, so it self-adjusts across different volatility regimes). This replaces the coarse "2 out of 5 conditions triggered" read with a comparable, ranked number.

  ⚠️ **What this score is *not***: it is still a hand-tuned rule-based weighting, exactly like every other threshold in this project — reusing signal_confluence.py's own condition thresholds so the two never silently drift apart. Nothing here has been back-tested against historical TAIEX returns. A score of "82/100" means "82 points' worth of this project's hand-picked bottom-supportive conditions are currently present" — **not** "82% probability of a bounce". The dashboard repeats this caveat next to the score, not just here.

### 🔬 TSMC (2330) Investment Score
2330 is the largest, most-watched holding in this project's watchlist, and it behaves differently from an ordinary ticker: TSMC's stock price usually trades *ahead* of its own reported results, on revisions to future earnings expectations (the monthly revenue trend, and the forward guidance given at each quarterly earnings call) — not on the trailing quarter's numbers in isolation. A pure KD/MACD/institutional-flow read, treated the same as any other stock in the watchlist, is structurally blind to that. `src/tsmc_analyzer.py` scores 2330 across 10 dimensions (100 points total), each degrading independently to "insufficient data" rather than guessing:

| Dimension | Points | What it measures |
|---|---|---|
| Revenue Momentum | 15 | Monthly revenue YoY (FinMind `TaiwanStockMonthRevenue`) — 3-month average and whether it's accelerating or decelerating, not just the latest single month |
| Margin / EPS Trend | 10 | Quarterly gross-margin momentum + EPS YoY (FinMind `TaiwanStockFinancialStatements`) — revenue growth ≠ profit quality |
| Guidance | 15 | See below — auto-fetched from TSMC's own IR site, no manual data entry needed anymore |
| Technical Trend | 15 | MA20/60/120 stack structure (price > MA20 > MA60 > MA120 = full bullish alignment) |
| Momentum (composite) | 10 | KD + RSI + MACD scores **averaged, not summed** — see caveat below |
| Relative Strength | 10 | 2330's own N-day return vs. TAIEX / SOX / NDX over the same window |
| Institutional / Chip | 10 | Per-stock foreign flow (already fetched — see "Per-Stock Institutional Flow" above) cross-referenced against price direction: confirmation, divergence, or possible absorption |
| ADR Premium/Discount | 5 | TSM (NYSE ADR, 1 ADR = 5 ordinary shares) implied 2330 price vs. 2330's actual price, via USD/TWD |
| Market Regime | 5 | Reuses `market_regime.py`'s classification directly |
| Valuation | 5 | Trailing PER percentile within 2330's own 3-year history (FinMind `TaiwanStockPER`) — a good company isn't automatically a good price |

⚠️ **The Momentum dimension is deliberately an average, not a sum**: KD, RSI, and MACD are all derived from the same underlying price series and are highly correlated — summing three correlated readings as if they were three independent confirmations overstates confidence. "Three indicators agree" isn't three times more reliable than one when the three aren't actually independent.

**Guidance — auto-fetched from TSMC's own official IR site.** An earlier version of this dimension used a fully hand-maintained file on the assumption that TSMC's structured guidance figures simply weren't available for free. That assumption was wrong: `fetcher.fetch_tsmc_official_guidance()` scrapes `investor.tsmc.com/english/quarterly-results` (which auto-redirects to whichever quarter was most recently reported) and reads its "Guidance" table directly — Actual, Guidance-given-for-that-quarter, and newly-issued Guidance-for-next-quarter, for Net Revenue, Exchange Rate, Gross Margin, and Operating Margin, **already in USD** (no NTD/USD conversion approximation needed). `main.py`'s `_update_tsmc_guidance_auto()` persists this into `data/tsmc_guidance_auto.json` append-only (each quarter's entry is frozen the first time it's seen, never rewritten later, to avoid backfill/look-ahead bias), building three sub-scores: **Guidance Revision** (0-6, this quarter's newly-issued guidance vs. the company's own prior guidance), **Revenue Actual vs. Guidance** (0-5, beat/miss vs. the guidance given for that exact quarter), and **Margin Actual vs. Guidance** (0-4, gross + operating margin each scored beat/in-line/miss — not possible at all in the old approach). What genuinely still has no free, point-in-time-safe source is third-party analyst **Consensus** — that's a deliberately different, harder problem (scattered sources, no reliable historical snapshots, and a real look-ahead-bias risk if queried naively for a past quarter) and stays out of scope here; every figure this dimension uses is tagged `benchmark_type="GUIDANCE"` and is never mixed with Consensus. `data/tsmc_guidance.json` remains as a small manually-seeded fallback covering the quarters before the auto-fetch existed — the auto-fetched value always wins when both exist for the same quarter.

**Three named buy-point setups**, each requiring both a fundamental-quality gate AND a market-timing trigger (so a good company at a stretched price, or a falling knife with no fundamental support, qualifies for neither):
- **基本面回撤買點 (Fundamental Pullback)**: fundamentals still strong, but price/KD show a short-term oversold overreaction.
- **趨勢突破買點 (Trend Breakout)**: fundamentals + technical structure + volume + foreign buying all confirm together — a "chase the confirmed move" setup.
- **恐慌反轉買點 (Panic Reversal)**: fundamentals hold up while the broader market panics — this one explicitly reuses Signal Confluence's B1-B3 bottom conditions (VIX reversal, margin capitulation, foreign short-covering) rather than re-deriving its own panic logic, per the same reasoning as the Market Regime dimension: 2330 is this project's best single lens on "is this a real crisis or a market-wide overreaction that fundamentals don't support."

Same caveat as everywhere else in this project: this is a hand-tuned rule-based weighting, not a back-tested statistical model.

### 🚧 Roadmap | 尚待開發
Ordered by where the next quantitative-rigor gain is largest, per two architecture reviews of this project (2026-08-09). Items 1-4 came out of the second review (code-level read of `kd_calculator.py`/`signal_confluence.py`) — Phase 1 of that review (date-alignment correctness) and the KD State engine are now **done** (see "KD Engine & Data-Integrity Fixes" above); everything below is what's still open, in the reviewer's own suggested order:
1. **Signal Confluence: boolean thresholds → graduated 0-100 sub-scores per condition**: T1-T5/B1-B3 in `signal_confluence.py` still evaluate as hard AND/OR booleans (e.g. "US 10Y 5-day change ≥ 0.15pp" is a cliff — 0.14pp and 0.15pp are barely different market states but flip the condition from 0 to 1 with nothing in between). `signal_score.py` already restructures the *rollup* of these conditions into a 0-100 score, but each individual contributing check inside it is still binary before being summed. The suggested fix is a graduated scale per indicator (e.g. US10Y 5D change: <0.00→0, 0.00-0.05→20, 0.05-0.10→40, 0.10-0.15→60, 0.15-0.25→80, >0.25→100) feeding into both modules, plus specifically upgrading B3 (FX stabilization + foreign flow reversal + futures covering) into its own weighted 0-100 "Bottom Reversal Score" (30/35/35 split) as a concrete worked example. Not yet started — the largest remaining design change from the second review.
2. **Signal History + Backtest**: log every signal-confluence/score event with the market state at the time, then automatically compute forward 1D/3D/5D/10D/20D returns, win rate, average return, expectancy, max drawdown, and Sharpe per signal type — the concrete next step that turns Signal Score from "how many conditions are met" into an actual back-tested statistic. Should eventually cover `tsmc_analyzer.py`'s score/buy-point setups too, not just Signal Score/Confluence — 2330's 10-dimension weights (15/10/15/15/10/10/10/5/5/5) are just as un-validated as everything else in this project. Not yet started.
   *   ℹ️ Note: `data/tsmc_guidance.json`'s manual-maintenance burden is now gone — Guidance is auto-fetched each run (see "TSMC (2330) Investment Score" above). No more quarterly hand-updates needed; the manual file is a fallback only.
3. **Flow normalization (Z-score / percentile / ratio)**: the per-stock institutional flow filter currently uses a flat 500-張 threshold on 3-day cumulative foreign net buy/sell, which treats a mega-cap like 2330 the same as a small-cap — normalizing against each stock's own 20-day average volume (or a 60-day Z-score) would make the threshold comparable across stocks. Not yet started.
4. **Data Freshness + source-specific scheduling**: most of this project's data (institutional flow, margin balance, TAIFEX futures, options P/C ratio) is EOD, not intraday, so the current blanket hourly cron does a lot of redundant fetching against unchanged data; splitting the schedule by source (US market data hourly, TW EOD data once/trading day) and surfacing a 🟢/🟡/🔴 freshness badge per indicator (so it's clear TAIEX is "today" while foreign flow might be "yesterday's report") are both still open. Not yet started.
5. **CPI/PCE, Non-Farm Payrolls & Unemployment Rate | CPI/PCE、非農就業與失業率**: Fetchable for free via FRED's no-key CSV endpoint, but these are monthly releases (not continuous prices) — they need a different "latest value + release date + countdown" UI treatment rather than the hourly ticker-card style, so they're deferred rather than shoehorned in. Lower priority than the quantitative-rigor items above.
   *   可透過 FRED 免金鑰 CSV 端點免費取得，但這些是月度公布數據（非連續價格），需要另一種「最新公布值+公布日期+倒數」的呈現方式，而非現有的每小時卡片樣式，因此先不做。優先度低於上述量化嚴謹度相關項目。
6. **ISM Manufacturing PMI**: Not planned — ISM revoked FRED's license to redistribute this data in 2016, and there's no reliable free official source anymore (real-time PMI is generally paywalled via Trading Economics/Bloomberg).
   *   不在計畫內——ISM 已於 2016 年收回 FRED 的資料授權，目前沒有可靠的官方免費來源（即時 PMI 多半來自付費資料商）。
7. **Git repository housekeeping | Git 倉庫維護**: `docs/data/` was added to `.gitignore` (it's a deploy-time build artifact and shouldn't be version-controlled), but the already-tracked copy still needs a one-time `git rm -r --cached docs/data` to actually stop tracking it.
   *   `docs/data/` 已加入 `.gitignore`（這是部署時才產生的建置產物，不該進版控），但既有已追蹤的檔案還需要手動跑一次 `git rm -r --cached docs/data` 才會真正停止追蹤。
8. **TSMC earnings-call transcript → structured extraction**: `investor.tsmc.com` also publishes each quarter's earnings-conference transcript PDF for free, which contains richer color (customer/platform revenue mix commentary, capex rationale, AI/HPC demand commentary) than the numeric Guidance table alone. An LLM-based structured-extraction pass over the transcript (a fixed JSON schema: revenue by platform, key qualitative guidance callouts, analyst Q&A themes) was floated as a strong follow-on but is lower priority than the backtest/normalization items above. Not started.
9. **Self-built "TSMC Market Expectation Index"**: as a longer-run substitute for true Street Consensus (which remains out of scope — see the Guidance section above), combine TSMC's own guidance + monthly revenue trend + supply-chain proxies (NVDA/AVGO/AMD/ASML) + SOX + TSM ADR direction into a single composite "is the market's implicit expectation for TSMC rising or falling" index. Lower priority, explicitly deferred by the project owner's own ranking. Not started.
10. **Analyst Consensus API (e.g. Financial Modeling Prep) — deferred**: a real Consensus data source exists but was deliberately deprioritized over reliability/licensing/point-in-time concerns — see the look-ahead-bias risk noted in the Guidance section above (querying "today's" consensus for a historical quarter already reflects information the market didn't have at that time, which is more dangerous for backtesting than having no consensus data at all). If pursued, would need explicit point-in-time snapshot handling, not a naive "fetch latest" call. Lowest priority, last in the project owner's own ranking.

---

<a name="繁體中文"></a>
## 🌐 繁體中文說明

這是一個利用 GitHub Actions 驅動的股票監控系統，追蹤台股與美股的 KD 指標。具備**每小時**自動資料更新功能，並透過 GitHub Pages 提供互動式儀表板。

### ✨ 核心功能
- 📈 **KD 指標追蹤**：自動計算所有監控股票的 9 日隨機指標 (KD)。
- 🔔 **智能警示**：當 KD ≥ 80 (超買) 或 ≤ 20 (超賣) 時自動發出提醒，並附上 MA／布林通道／MACD 多重濾網信心標籤，標示可能的指標鈍化（詳見下方說明）。
- 🇹🇼 **台股支援**：支援台股代碼 (如 0050.TW, 2330.TW)。
- 🇺🇸 **美股支援**：支援美股代碼 (如 AAPL, TSLA)。
- 🌐 **網頁儀表板**：提供圖表與即時數據的互動式介面。台股大盤（加權指數）與台指期夜盤跳空放在頁面最上方最顯眼的位置。
- 🌍 **全球宏觀指標**：VIX、美債 10Y、美元指數、比特幣、原油 (WTI)、黃金，以及費半 (SOX)、那斯達克100、標普500——真正牽動台股科技/半導體權值股的指數，而非道瓊。
- 🇹🇼 **台股籌碼面**：外資/投信買賣超、融資融券餘額、新台幣匯率（TWSE 開放資料），外資台指期淨部位、選擇權 P/C Ratio（FinMind），以及追溯性的台指期夜盤跳空指標。
- 🎯 **訊號共振模型**：交叉驗證宏觀指標、台股籌碼面、衍生性商品與科技指數指標，判斷大盤頂部/底部轉折，所有條件皆可完整驗證（詳見下方說明）。
- ⚡ **自動更新**：透過 GitHub Actions 進行**每小時**自動化抓取與部署。
- 📱 **行動裝置優化**：響應式設計，適合手機查看。

### 📉 交易模式分析
系統自動分析以下 11 種市場模式：
1. 🔴 **快漲慢跌** (主力出貨)：通常為賣出訊號。
2. 🟢 **快跌慢漲** (主力吸籌)：通常為買入訊號。
3. 🔴 **放量上漲** (見頂風險)：可能是見頂風險，建議賣出。
4. ⚫ **縮量不跌** (頭部形成)：可能是頭部形成，建議避開。
5. 🟡 **縮量上漲** (趨勢健康)：代表趨勢健康，建議持有。
6. ⚫ **縮量下跌** (繼續看跌)：代表買盤不足，建議繼續看跌。
7. 🔴 **縮量不漲** (頭部確立)：通常是頭部確立，建議賣出。
8. 🟢 **放量下跌** (恐慌殺跌)：可能是分批買入機會。
9. 🟢 **恐慌底部** (短線搶反彈)：極嚴格信號，一年僅數次。
10. 🔴 **天量噴出** (必然回落)：極嚴格信號，短線過熱極端。
11. 🟢 **籌碼鎖定** (主升延續)：極嚴格信號，籌碼高度鎖定的強勢主升。

### 🛡️ KD 警示多重濾網（防指標鈍化）
KD 是一個「震盪型指標」，假設股價會在箱型區間內來回波動。強烈趨勢中它會「鈍化」——單純 `KD ≥ 80` 在飆股主升段可能連續發出數週警示（誘使過早賣出、錯失主升段），單純 `KD ≤ 20` 也無法區分「即將反彈」與「還在破底」。系統不會隱藏任何一次 KD 極端讀值（每次都仍會發出警示），但會套用與多維評分引擎共用的 MA／成交量／MACD／布林通道資料，為每一則警示標註信心等級：
- **高信心**：超賣情境下，股價站上上彎的 20 日均線之上（多頭趨勢中的回檔）且／或觸及布林通道下軌，MACD 未加速走弱。超買情境下，股價未能站穩上彎的 20 日均線之上，或股價觸及布林通道上軌但成交量未放大（動能不足，非真正強勢）。
- **疑似鈍化**：超賣情境下，股價在下彎的 20 日均線之下（真正空頭趨勢，無均線/布林支撐）或 MACD 仍加速走弱。超買情境下，股價仍穩穩站在上彎的 20 日均線之上且 MACD 仍加速走強（典型主升段鈍化，並非真正的頭部）。
- **資料不足**：歷史資料不到約 25 個交易日（新掛牌標的），濾網尚無法運作——原始 KD 警示仍會照常發出，只是不附上信心標籤。

具體套用了哪些濾網條件（通過與提醒的項目）會直接顯示在儀表板的每一則警示卡片上。每一則警示（以及每張個股卡片）現在也會附上 **KD 狀態**（見下一節）；待歷史資料累積足夠後，也會附上**市場狀態**標籤——詳見更下方的「市場狀態與訊號評分」如何影響這個確認門檻。

### 🔬 KD 引擎與資料完整性修正（2026-08-09）
針對 `src/kd_calculator.py` 與 `src/signal_confluence.py` 的程式碼層級審查，發現幾個在新增功能之前更值得先修正的正確性問題——記錄於此，因為這些修正會改變現有數值的意義，而不只是呈現方式。

- **RSV 除以零的處理明確化**：RSV（`100 * (收盤價 - 區間最低) / (區間最高 - 區間最低)`）在價格於回看期間內完全沒有波動時（例如暫停交易或極度冷門的標的）會產生除以零。過去是靠除法後的 `.fillna(50)` 統一補值——湊巧得到正確結果，但把「區間真的持平、50 本來就是 RSV 在此情境下的定義值」跟「這一列因不明原因壞掉」混為一談。現在明確處理：每列預設為 50，只有區間真的非零的列才會套用實際除法結果。
- **KD 初始化慣例明確寫入文件**：前 `k_period - 1` 列（預設 9 日設定下即前 8 列）會固定為 K=D=50，不參與遞迴公式（因為回看期間資料尚不完整），這原本就是程式的實際行為，只是沒有寫明。若拿去跟其他看盤軟體比對，這點值得注意，因為有些軟體的初始化方式不同（例如第一列直接以 RSV 作為 K/D），前幾列的數值會對不起來。
- **KD 狀態取代原本單一的超買/超賣/多頭/空頭/中性判讀**（`KDCalculator.analyze_kd_signal()`）。舊版 docstring 宣稱會回傳 `golden_cross`／`death_cross`，但函式實際上從未偵測交叉——這是真實的文件與實作不一致。現在會同時參考今日與昨日的 K/D（交叉方向、以及 K-D 差距是擴大還是收斂），分類為 10 種狀態：`GOLDEN_CROSS`（黃金交叉）、`DEATH_CROSS`（死亡交叉）、`OVERBOUGHT_BUT_RISING`（超買中但差距仍擴大——動能未歇，較可能是鈍化而非真正的頭部）、`OVERBOUGHT_REVERSAL`（差距收斂——較可能是真正的頭部）、`OVERBOUGHT`、`OVERSOLD_REVERSAL`（差距收斂、K 正回升向 D 靠攏——最明確的黃金交叉前兆／築底訊號）、`OVERSOLD_BUT_RISING`、`OVERSOLD`、`BULLISH_MOMENTUM`、`BEARISH_MOMENTUM`。這直接解決了舊分類器的一個實際缺口：K=95/D=80（差距寬、可能仍在擴大）與 K=95/D=94（差距幾乎收斂）過去都只會顯示「超買」，現在不會了。於 `calculate_all_stocks()` 中逐股計算，存為 `kd_state`，並顯示在每張個股卡片與每則警示上。
- **`signal_confluence.py`、`signal_score.py`、`market_regime.py` 三個檔案共通的時間軸對齊錯誤**：三者原本都是先把某欄位歷史中值為 `None` 的日期整個濾除，才取最後 N 筆數值——導致單一缺漏的一天會悄悄改變「連續3日」「5日變化」「200日均線」實際涵蓋的期間，且不會有任何錯誤或警告。例如原始資料 `8/1 -100, 8/2 None, 8/3 -200, 8/4 -300` 會被壓縮成 `[-100, -200, -300]`，此時「連續3日賣超」的檢查會把 8/1 跟 8/4 當作相隔3個交易日來比較，但實際上是4天。修正方式是把所有的日期回看／連續日／移動平均計算，全部改用 `_window()` / `_lookback()`（定義於 `signal_confluence.py`，另外兩個模組皆從此匯入）——這兩個函式要求整個回看區間內每一天都必須有值，只要區間內有一天缺漏就回報「資料不足」，而不會悄悄往更早的日期多抓一筆來湊數。唯一刻意保留寬鬆處理的例外是 `signal_score.py` 的 VIX 百分位排名（情緒面向）——這是一個分布性統計量，本來就不需要數值在日曆上連續，因此保留一個有明確註記的容錯收集函式（`_recent_values()`）。
- **T2「新台幣貶破整數關卡」條件**（原本是 `int(today) > int(prior)`）對於正的匯率數值而言在數學上等同於 `floor()`，所以並沒有算錯——但整數關卡的間距（NT$1）只是使用 `int()` 帶來的隱性副作用，而不是一個真正、有文件記載、可調整的參數。已改為明確的 `floor(數值 / 間距)` 比較，並新增 `TWD_ROUND_NUMBER_STEP` 常數。

### 📊 個股外資買賣超
除了台股籌碼面指標中原有的「大盤整體」外資／投信買賣超之外，現在每一檔個別追蹤的台股標的也會有自己的外資／投信／自營商買賣超（股數），資料來源為 FinMind 的 `TaiwanStockInstitutionalInvestorsBuySell`（上市、上櫃、ETF 皆適用）。這項資料會直接納入上方「KD 警示多重濾網」作為額外的確認訊號：超賣情境下若近 3 日外資累計買超、或超買情境下若近 3 日外資累計賣超，即使 MA／布林通道濾網未能確認，也能獨立確認該警示——個股外資的買賣動向本身就是有意義的訊號，不只是股價波動的附屬產物。此資料會顯示在每一張台股個股卡片上。

### 🔒 管理監控股票（僅限擁有者）
儀表板上有一個「管理監控股票」面板，可以新增或移除監控的股票——僅限本專案擁有者本人操作，且**網站本身不會儲存或要求任何帳號密碼、Token**。送出表單時會開啟一個預先填好內容的 GitHub「New Issue」，而不是直接呼叫任何 API。真正的權限判斷在一個獨立的 GitHub Action（`.github/workflows/stock-request.yml`）：只有當 Issue 是由 `github.repository_owner` 本人開啟時才會執行，其他人開的申請完全不會有任何反應（不留言、不變更設定）。當它真的執行時，會解析 Issue 內容、透過 `scripts/apply_stock_request.py` 更新 `config.json`、提交變更，並在 Issue 留言告知結果後自動關閉——推送變更後會自動觸發每小時的資料更新流程，幾分鐘內就能看到新增/移除的標的生效。這個設計刻意避開了在瀏覽器儲存 GitHub Token 的做法——先前曾經有過把 PAT 存在 `localStorage` 的版本，因為風險考量已經移除（見 commit `53fc74560`）。

### 📰 重大財經新聞
儀表板上有一個「重大財經新聞」面板，每小時自動從 **Yahoo奇摩股市**（`tw.stock.yahoo.com/news`）抓取最新的大盤／宏觀財經頭條——這是 Yahoo 旗下真正獨立、原生繁體中文的新聞站台，不是英文版 `finance.yahoo.com` 的機器翻譯。它的財經新聞涵蓋 Fed／總經、美股、陸港股、黃金、外匯，還多了英文版沒有的台股專屬新聞，因此換成這個來源同時拿到了「原生中文」與「更完整涵蓋範圍」，也不需要額外加一道翻譯步驟（多一個 API 依賴、成本、以及翻譯品質風險）。這是整個系統中最脆弱的資料來源，但也是不得已的選擇：截至 2026 年，Yahoo 已經沒有可用的公開新聞 API 了——實測過 `yfinance` 內建的新聞查詢，以及 Yahoo 舊版 RSS（`feeds.finance.yahoo.com/rss/2.0/headline`），兩者都回傳空白或被封鎖，只有直接抓取新聞頁面能真的拿到內容。`fetcher.py` 的 `fetch_market_news()` 是依「網址格式」（Yahoo Finance／Yahoo奇摩股市的文章網址都以 `-<6位數以上ID>.html` 結尾）而非 CSS class 名稱來解析——網址格式通常比排版結構更能撐過網站改版，但如果 Yahoo 整個改了網址規則，或是從 GitHub Actions 的 IP 被擋下來，這裡還是有可能抓不到任何東西。這個功能永遠是靜默失敗（回傳空清單、記錄警告），不會影響其他功能；抓不到新聞時，儀表板上就會顯示「暫無新聞」。

### 🇹🇼 台股大盤（TAIEX/加權指數）
在儀表板最上方最顯眼的位置顯示——這是本專案真正要監控的指數本體，不只是眾多輔助宏觀指標之一。旁邊搭配顯示台指期夜盤跳空（見下方台股籌碼面指標項目 6）——兩者放在一起，因為夜盤正是 TAIEX 下一個開盤的隔夜前哨。

### 🌐 宏觀指標
1. **VIX 恐慌指數**: 衡量市場波動度與恐慌情緒。高 VIX (>30) 通常代表恐慌，可能是分批買點。
2. **美債 10 年期收益率**: 無風險利率的基準。收益率上升會對股市估值造成壓力，尤其是科技股。
3. **美元指數**: 衡量美元強度。強勢美元通常會對新興市場與大宗商品價格產生壓力。
4. **比特幣**: 通常被視為高風險資產的代表。其趨勢反映了市場對風險的整體偏好程度。
5. **原油 (WTI)**: 生產與運輸成本的代表。油價飆升會引發輸入型通膨，壓抑企業利潤，並迫使央行維持高利率。
6. **黃金**: 對沖地緣政治風險與法幣貶值的工具，可與比特幣（高風險偏好）互補觀察市場情緒。
7. **費城半導體指數 (SOX)**：台股加權指數本質上是「科技/半導體重壓指數」（台積電及其供應鏈佔絕對權重），SOX 的轉折是台股轉折的「源頭定價」訊號，預測力遠高於道瓊（傳統藍籌工業股，與台股獲利/資金連動性極低）。
8. **那斯達克100指數 (NDX)**：涵蓋全球主要科技巨頭（如 Apple、NVIDIA），這些公司是台股電子供應鏈訂單的終端大客戶。
9. **標普500指數**：反映美國整體總體經濟狀況的標準指標，用於判斷美國是否步入衰退。

### 🇹🇼 台股籌碼面指標
項目 1–3 資料來源為台灣證交所 (TWSE) 官方免費開放資料，無需 API 金鑰；項目 4–6 來自 FinMind 開放資料 API (`api.finmindtrade.com`，免費額度、無需金鑰，可選填 `FINMIND_TOKEN` 環境變數以提高流量上限)。這些皆為每日收盤後才會公布的資料，並非即時報價，儀表板會標示每個數值實際對應的交易日。

1. **外資 / 投信買賣超**：來自「三大法人買賣金額統計表」的全市場淨買賣金額。外資占台股市值比重極高，是加權指數中長期方向的主要驅動力；投信資金對中小型股與 ETF 成分股影響力較大。
2. **融資融券餘額與資券比**：來自「信用交易統計」。融資餘額代表散戶槓桿多頭力道，融券餘額代表空頭部位。融資餘額單日大減（俗稱「融資斷頭」）是散戶籌碼洗淨最客觀的訊號之一。
3. **新台幣匯率**：外資進出台股的領先/同步指標。新台幣升值通常伴隨外資匯入，持續貶值則通常伴隨外資撤出。
4. **外資台指期未平倉淨部位**：外資在台指期的多空未平倉淨部位（`TaiwanFuturesInstitutionalInvestors` 資料集）。若現貨賣超同時期貨呈現大量淨空單，代表外資不只是調節現貨，而是在避險或看空後市。
5. **選擇權 Put/Call Ratio**：台指選擇權 (TXO) put/call 未平倉量比（`TaiwanOptionDaily` 資料集）。比值偏低代表市場偏多、樂觀情緒濃厚，接近頭部風險；比值走高則代表避險/恐慌需求上升。
6. **台指期夜盤跳空**：近月台指期夜盤（台北時間 15:00–05:00）收盤價 vs. 前一交易日盤收（`TaiwanFuturesDaily`，`trading_session=after_market`）。這是**追溯性**資料——FinMind 只在約台北時間 16:30 的每日批次中一次公布完整的日盤+夜盤資料，與項目 1–5 同一節奏。這**不是**能在夜盤當下即時操作的盤中報價；真正即時的資料需要 FinMind 付費 sponsor 方案的即時快照端點，本專案並未使用。

### 🎯 訊號共振：大盤轉折模型
不單看任何單一指標——這個模型（`src/signal_confluence.py`）只有在**多項獨立條件同時出現共振**時才會標示可能的轉折點，交叉驗證全球宏觀資金、匯率與台股籌碼面。

**頂部結構與避險啟動訊號**（風險升高）：
- 宏觀資金抽離：DXY 突破前高，且美債 10Y 快速攀升。
- 匯率表態：新台幣連續走貶或貶破整數關卡。
- 外資期現貨雙空：現貨連續賣超，且台指期淨部位達重度空單門檻。
- 籌碼過度樂觀/散戶接刀：外資倒貨同時融資餘額不退，且選擇權 P/C Ratio 偏低（市場過度樂觀）。
- 科技資金退潮：費半 (SOX) 或那斯達克100 (NDX) 跌破近期支撐，且美債 10Y 快速攀升——「源頭定價」機制，因台股加權指數本質上是科技/半導體重壓指數。

**底部轉折與加碼訊號**（危機解除）：
- 恐慌極值反轉：VIX 飆高後見頂回落。
- 散戶投降：融資餘額斷頭式大減。
- 匯率止穩、外資現貨轉買，且台指期空單回補中。

以上所有條件現在皆可完整驗證——台指期淨部位與選擇權 P/C Ratio 已透過 FinMind 取得（見台股籌碼面指標項目 4–5）。在每日歷史資料（`data/macro_history.json`）累積足夠天數之前，各條件會回報「資料不足」而非誤判觸發。面板本身要累積滿 **21 個交易日**（約 1 個月）才會開始評估——這個天數對齊了最長的單一條件視窗（T1 的 DXY 突破前高與 T5 的 SOX/NDX 跌破支撐都需要 20 日回看期+當日），確保面板一旦顯示「開始評估」，所有條件都真正有機會判斷，而不是有兩三個條件在面板已顯示「可用」後還要再卡兩週才會有結果。

不需要真的等三週的每小時執行才能累積出這些歷史資料：只要歷史資料還不夠長，第一次執行時會自動做**一次性歷史回填**（`fetcher.backfill_macro_history()`）——`yfinance` 每檔標的只要一次呼叫、FinMind 每個資料集只要一次區間查詢，就能一口氣拿到好幾週的歷史；只有 TWSE 的籌碼面資料（外資/投信買賣超、融資餘額）需要逐日迴圈抓取，因為 TWSE 的免費報表不支援區間查詢。這個逐日迴圈是最慢的部分（最多約 70 次連續請求，約需幾分鐘，並在每次請求間加入短暫延遲以善待這個免費公開端點），但只會執行一次——一個標記檔案（`data/.macro_backfill_done`）會避免它每小時重跑，即使只有部分成功也一樣。想強制重跑的話刪除該標記檔案即可。回填只會補齊缺漏的欄位，絕不會覆蓋一般執行已經記錄下來的真實數值。

台指期夜盤跳空（項目 6）在儀表板上作為輔助參考顯示——呈現昨夜跳空的幅度——但並未納入訊號共振的條件判斷，因為這是追溯性資料（要到日盤已經開盤反應過後才能取得）。

⚠️ 依照模型本身的設計初衷：這是單筆大額加碼或停止追高的參考依據，**並非**頻繁進出或放空訊號。若本身在對大盤型 ETF（如 0050）執行定期定額策略，讓短線期貨/籌碼雜訊觸發「動態避險」，一旦判斷錯誤，避險成本通常比它省下的還多。

### 🧭 市場狀態與訊號評分（Market Regime & Signal Score）
專案目前的門檻式條件（上述 T1–T5 / B1–B3，以及個股 KD 濾網）本質上都還是人工設定的規則——把好幾條規則合併成「N 項條件成立」，並不會讓結果自動變成經過驗證的統計優勢。這兩個新模組是朝更嚴謹架構邁進的第一步，針對性解決兩個具體缺口：**同樣的原始讀數，在不同市場背景下代表的意義不同**，以及**「N/5 項共振」的布林值表示法，掩蓋了訊號實際上有多強或多弱**。

- **市場狀態**（`src/market_regime.py`）依 `data/macro_history.json` 的資料，將目前市場背景分類為五種狀態之一：**多頭趨勢**（TAIEX 站上長天期均線，且均線仍上揚）、**多頭回檔**（仍在均線之上，但均線已走平/下彎）、**空頭趨勢**（跌破均線，且未見回穩訊號）、**恐慌急殺**（VIX 急升且已達高檔——不論當時趨勢位置為何，皆屬急性壓力狀態）、**築底回穩**（VIX 自近期高點回落，且外資資金流由賣轉買——屬於壓力解除後的過渡狀態）。均線週期採自適應設計（200/120/60/20 日階梯，取現有歷史資料能支援的最長週期），而非寫死 200 日——因為 `backfill_macro_history()` 首次執行僅回填約 35 天，要累積滿 200 個交易日需要數個月時間，儀表板會明確標示實際採用了哪個均線週期。
  這個市場狀態標籤會直接餵入個股 KD 警示濾網（`alert_checker.py` 的 `_evaluate_filters`）：同樣一個 KD≤20 的讀數，在多頭回檔或築底回穩的背景下會**降低**確認門檻（符合「逢低承接」的情境），在空頭趨勢或恐慌急殺的背景下則會**提高**確認門檻（避免接刀風險）——而不是不論大盤處於什麼狀態都用同一套標準判斷。每筆警示現在也都會附上 `market_regime` / `market_regime_label`，讓儀表板能明確標示這次確認判斷是基於哪種市場背景做出的。

- **訊號評分**（`src/signal_score.py`）將「訊號共振」使用的同一批底層資料，重新表示成兩個 0-100 分的分數——**頂部風險分數**與**底部佈局分數**——各自拆解為五個加權面向：總經 Macro（0-25）、籌碼 Chip Flow（0-25）、衍生性商品 Derivative（0-20）、技術面 Technical（0-20，直接對 TAIEX 自身的收盤價計算 20 日布林通道 + RSI(14)，而非任何個股）、情緒面 Sentiment（0-10，採 VIX 在自身歷史滾動視窗中的百分位排名，而非固定門檻，讓判斷標準能隨不同波動度時期自動調整）。這取代了原本粗略的「5項中有2項成立」表示法，改為可比較、可排序的數字。

  ⚠️ **這個分數不是什麼**：它仍然是人工設定權重的規則式評分，跟本專案其他所有門檻一樣——並重用 `signal_confluence.py` 本身的條件門檻，確保兩個模組不會悄悄產生分歧。目前尚未對 TAIEX 歷史報酬進行任何回測驗證。「82分」的意思是「目前有82分權重的已知底部支撐條件成立」，**不是**「82%機率會反彈」。儀表板上會在分數旁邊重複這個警語，而不只是寫在這裡。

### 🔬 台積電 (2330) 投資決策分數
2330 是本專案監控名單中最大、最受關注的持股，而且它的行為跟一般個股不一樣：台積電股價通常會**提前**反應「未來獲利預期的變化」（月營收趨勢、每季法說會給出的財測指引），而不是單純落後反應已公布的上一季數字。若把它跟名單中其他股票一樣，只用 KD/MACD/外資買賣超各自判斷，結構上就完全看不到這一塊。`src/tsmc_analyzer.py` 把 2330 拆成 10 個構面（總分100），每個構面各自獨立地在資料不足時回報「資料不足」，而不是用猜的：

| 構面 | 分數 | 衡量內容 |
|---|---|---|
| 營收動能 | 15 | 月營收年增率（FinMind `TaiwanStockMonthRevenue`）——採3個月均值並判斷是否加速/減速，而非只看單月 |
| 毛利率/EPS趨勢 | 10 | 季度毛利率動能 + EPS年增（FinMind `TaiwanStockFinancialStatements`）——營收成長不等於獲利品質 |
| 法說會財測指引 | 15 | 見下方說明——現已改為自動從台積電官方IR網站抓取，不再需要人工維護資料 |
| 技術趨勢 | 15 | MA20/60/120排列結構（股價>MA20>MA60>MA120＝完整多頭排列） |
| 動能綜合 | 10 | KD + RSI + MACD 分數**取平均而非加總**——原因見下方警語 |
| 相對強弱 | 10 | 2330自身N日報酬 vs. 同期台股大盤/費半/那斯達克100 |
| 外資籌碼 | 10 | 個股外資買賣超（已有此資料，見上方「個股外資買賣超」）與股價方向交叉比對：確認、背離、或可能吸收賣壓 |
| ADR溢折價 | 5 | TSM（紐約證交所ADR，1 ADR=5股普通股）換算的2330隱含價格 vs. 2330實際價格，透過USD/TWD換算 |
| 大盤環境 | 5 | 直接引用 `market_regime.py` 的市場狀態分類 |
| 估值 | 5 | 本益比在2330自身近3年歷史中的百分位（FinMind `TaiwanStockPER`）——好公司不代表好價格 |

⚠️ **動能構面刻意採「平均」而非「加總」**：KD、RSI、MACD 三者都源自同一條價格序列，彼此高度相關——把三個高度相關的讀值當成三個獨立的確認訊號直接加總，會高估其可信度。「三個指標同時看多」在三者本來就不是真正獨立的情況下，並不代表可信度是單一指標的三倍。

**法說會財測指引——現已自動從台積電官方IR網站抓取。** 早期版本因為誤判「台積電結構化財測指引無免費資料源」而採全人工維護，這個前提其實是錯的：`fetcher.fetch_tsmc_official_guidance()` 會抓取 `investor.tsmc.com/english/quarterly-results`（會自動導向最新一期公布的季別），直接讀取其「Guidance」表格——包含 Actual（實際數字）、Guidance-for-that-quarter（該季當初給的指引）、以及新公布的 Guidance-for-next-quarter（下一季新指引），涵蓋營收、匯率假設、毛利率、營益率四項，**且原始資料本身就是美元計價**（不再需要用USD/TWD快照匯率概略換算NT$實際值）。`main.py` 的 `_update_tsmc_guidance_auto()` 會把這些資料以 append-only 方式寫入 `data/tsmc_guidance_auto.json`（每一季的資料在第一次被看到時就凍結，之後不會被覆寫，避免回填/未來函數偏誤），並拆成三個子分數：**Guidance Revision**（0-6分，本季新公布的指引 vs. 公司自己上一筆指引的QoQ變化）、**Revenue Actual vs. Guidance**（0-5分，實際營收 vs. 當初該季指引的beat/miss）、以及**Margin Actual vs. Guidance**（0-4分，毛利率+營益率分別評估beat/in-line/miss——這在舊作法中完全無法計算）。真正還是沒有免費、時間點安全（point-in-time-safe）資料源的，是第三方分析師的**市場共識（Consensus）**——這是刻意區分開、更困難的另一個問題（來源零散、沒有可靠的歷史快照、且若對歷史某一季天真地查詢「現在的」共識，會有真實的未來函數偏誤風險），因此不在此構面範圍內；本構面所有數字都標記為 `benchmark_type="GUIDANCE"`，絕不與Consensus混用。`data/tsmc_guidance.json` 仍保留作為自動抓取涵蓋範圍之前季別的人工種子備援——同一季別若兩者都有資料，永遠以自動抓取版本為準。

**三種具名買點設定**，每一種都同時要求「基本面門檻」與「市場時機觸發」兩個條件都成立（避免「好公司但價格已過度反應」或「純粹接刀、基本面沒有支撐」都被誤判為買點）：
- **基本面回撤買點**：基本面仍強，但股價/KD顯示短線出現超賣式的錯殺。
- **趨勢突破買點**：基本面＋技術面排列＋量能＋外資買超同步確認——「確認後追價」的設定。
- **恐慌反轉買點**：大盤恐慌但2330基本面沒有同步惡化——這一項刻意直接重用「訊號共振」的 B1-B3 底部條件（VIX反轉、融資斷頭、外資空單回補），而非另外重造一套恐慌邏輯，理由跟「大盤環境」構面一致：2330 是本專案觀察「這是真正的危機，還是基本面沒有支撐的市場過度反應」最好的單一觀察標的。

跟本專案其他所有地方一樣的警語：這是人工設定權重的規則式評分，並非經過回測驗證的統計模型。

### 🚧 尚待開發
依兩次架構審查（2026-08-09）評估下一步量化嚴謹度效益最大的項目排序。第 1-4 項來自第二次審查（對 `kd_calculator.py`/`signal_confluence.py` 的程式碼層級審查）——該次審查的 Phase 1（時間軸對齊正確性）與 KD 狀態引擎現在**已完成**（見上方「KD 引擎與資料完整性修正」），以下是照審查者建議順序排列、尚未完成的項目：
1. **訊號共振：布林值門檻 → 每項條件獨立的 0-100 漸進式評分**：`signal_confluence.py` 中的 T1-T5/B1-B3 目前仍是硬性 AND/OR 布林判斷（例如「美債10Y 5日變動 ≥ 0.15pp」是一個斷崖式門檻——0.14pp 跟 0.15pp 幾乎是同一個市場狀態，但條件會直接從 0 跳到 1，中間沒有過渡）。`signal_score.py` 已經把這些條件的「彙總方式」改成 0-100 分數，但內部每一個獨立的判斷條件加總前仍然是二元的。建議做法是為每個指標建立漸進式量表（例如美債10Y 5日變動：<0.00→0、0.00~0.05→20、0.05~0.10→40、0.10~0.15→60、0.15~0.25→80、>0.25→100），同時餵入兩個模組；並具體把 B3（匯率止穩＋外資轉買＋期貨回補）升級成獨立的加權 0-100「底部反轉分數」（30/35/35 拆分）作為具體範例。尚未開始——這是第二次審查中最大的待完成設計變更。
2. **訊號事後績效追蹤 + 回測（Signal History + Backtest）**：記錄每次訊號共振/評分事件發生當下的市場狀態，之後自動計算後續 1D/3D/5D/10D/20D 報酬率、勝率、平均報酬、期望值、最大回撤與 Sharpe——這是讓「訊號評分」從「目前有多少條件成立」進化成真正經過回測驗證的統計數據的具體下一步。未來也應該涵蓋 `tsmc_analyzer.py` 的分數/買點設定，不只是訊號評分/共振——2330 的10個構面權重（15/10/15/15/10/10/10/5/5/5）跟本專案其他所有權重一樣，目前都還沒經過驗證。尚未開始。
   *   ℹ️ 備註：`data/tsmc_guidance.json` 的人工維護負擔現已解除——法說會財測指引現在每次執行都會自動抓取（見上方「台積電 (2330) 投資決策分數」）。不再需要每季手動更新，人工檔案僅作為備援。
3. **籌碼流量標準化（Z-score / 百分位 / 比率）**：目前個股法人流向濾網對 3 日累計外資買賣超採用固定 500 張門檻，會把台積電這種大型權值股跟小型股一視同仁；改為以個股自身 20 日均量正規化（或 60 日 Z-score）才能讓門檻在不同股票間具有可比性。尚未開始。
4. **資料時效 + 依資料源分別排程**：本專案多數資料（法人買賣超、融資餘額、台指期、選擇權 P/C 比）本質上是收盤後（EOD）資料而非盤中即時資料，目前每小時統一執行的排程對未變動的資料做了大量重複抓取；將排程依資料源拆分（美股資料每小時、台股 EOD 資料每個交易日一次）並在每項指標旁顯示 🟢/🟡/🔴 資料新鮮度標示（讓使用者清楚 TAIEX 是「今天」的資料、而外資買賣超可能是「昨天」的報告），這兩項都還未開始。
5. **CPI/PCE、非農就業與失業率**：可透過 FRED 免金鑰 CSV 端點免費取得，但這些是月度公布數據（非連續價格），需要另一種「最新公布值+公布日期+倒數」的呈現方式，而非現有的每小時卡片樣式，因此先不做。優先度低於上述量化嚴謹度相關項目。
6. **ISM 製造業 PMI**：不在計畫內——ISM 已於 2016 年收回 FRED 的資料授權，目前沒有可靠的官方免費來源（即時 PMI 多半來自付費資料商）。
7. **Git 倉庫維護**：`docs/data/` 已加入 `.gitignore`（這是部署時才產生的建置產物，不該進版控），但既有已追蹤的檔案還需要手動跑一次 `git rm -r --cached docs/data` 才會真正停止追蹤。
8. **台積電法說會逐字稿 → 結構化擷取**：`investor.tsmc.com` 也免費公布每季法說會逐字稿PDF，內容比純數字財測指引表更豐富（客戶/平台營收結構評論、資本支出理由、AI/HPC需求評論等）。用LLM對逐字稿做結構化擷取（固定JSON schema：分平台營收、關鍵定性財測描述、法人問答主題）是一個被提出的強力延伸方向，但優先度低於上方回測/正規化項目。尚未開始。
9. **自建「台積電市場預期指數」**：作為真正市場共識（Consensus，見上方財測指引說明，仍不在範圍內）的長期替代方案，將台積電自身財測＋月營收趨勢＋供應鏈代理指標（NVDA/AVGO/AMD/ASML）＋SOX＋TSM ADR方向整合成單一「市場對台積電的隱含預期正在上升或下降」綜合指數。優先度較低，依專案擁有者自己的排序明確列為延後項目。尚未開始。
10. **分析師市場共識API（例如Financial Modeling Prep）——延後**：確實存在真正的Consensus資料源，但因可靠性/授權/時間點完整性考量而刻意降低優先度——見上方財測指引說明中提到的未來函數偏誤風險（對歷史某一季查詢「今天的」共識，其實已經包含當時市場還不知道的後續資訊，這比完全沒有共識資料更危險，尤其用於回測時）。若真要做，需要明確處理「時間點快照」而非天真地「抓最新」。優先度最低，依專案擁有者自己的排序列為最後一項。

---

## 🚀 Quick Start | 快速上手

### Prerequisites | 前置條件
- Python 3.11+
- Git

### Installation | 安裝步驟
```bash
git clone https://github.com/blessyeh/kd-stock-monitor.git
cd kd-stock-monitor
pip install -r requirements.txt
```

### Run Locally | 本地執行
```bash
cd src
python main.py
```

---

## 🚀 Deployment & Usage | 部署與使用

### Deploying to GitHub Pages | 部署至 GitHub Pages
Follow these steps to deploy your own instance of the KD Stock Monitor on GitHub Pages.
請遵循以下步驟，將您自己的 KD 股票監控器部署到 GitHub Pages。

1.  **Fork the Repository | Fork 此專案**: Click the "Fork" button at the top-right of this page to create a copy of this project in your GitHub account.
    *   點擊頁面右上角的 "Fork" 按鈕，將此專案複製一份到您自己的 GitHub 帳號下。
2.  **Enable Actions | 啟用 Actions**: In your forked repository, go to the `Actions` tab and click the "I understand my workflows, go ahead and enable them" button. This is required for automatic data updates and deployment.
    *   在您 Fork 的專案中，前往 `Actions` 頁籤，點擊 "I understand my workflows, go ahead and enable them" 按鈕以啟用工作流程。這是實現自動化資料更新與部署的必要步驟。
3.  **Trigger the Deployment | 觸發部署**:
    *   Still in the `Actions` tab, click on `Hourly Stock Update & Deploy` on the left sidebar.
    *   Click the `Run workflow` dropdown, then the green `Run workflow` button. This will start the first build and deployment process.
    *   仍在 `Actions` 頁籤，點擊左側的 `Hourly Stock Update & Deploy`，接著點擊 `Run workflow` 下拉選單，並按下綠色的 `Run workflow` 按鈕。這會開始第一次的建置與部署流程。
4.  **Configure and Visit Your Site | 設定並瀏覽您的網站**:
    *   Wait for the workflow to complete (it may take 2-3 minutes).
    *   Go to your repository's `Settings` > `Pages` tab.
    *   You should see a message "Your site is live at `https://<Your-Username>.github.io/<Your-Repo-Name>/`". Visit this URL to see your monitor.
    *   If not already configured, set the `Source` under `Build and deployment` to `GitHub Actions`.
    *   等待工作流程執行完畢 (約需 2-3 分鐘)，然後前往專案的 `Settings` > `Pages` 頁籤。您會看到網站已發佈的網址，例如：`https://<您的帳號>.github.io/<專案名稱>/`。如果頁面尚未設定，請在 `Build and deployment` 的 `Source` 選擇 `GitHub Actions`。

### Using the Web Interface Locally | 在本地端使用網頁介面
You can run the web dashboard on your local machine to view the latest data you've fetched.
您可以在本機電腦上運行網頁儀表板，以查看您已抓取的最新數據。

1.  **Fetch Data | 抓取資料**: First, run the Python script to fetch the latest stock data. This will populate the `/data` directory.
    *   首先，執行 Python 腳本以抓取最新的股票數據，這會將資料填入 `/data` 資料夾。
    ```bash
    python src/main.py
    ```
2.  **Copy Data to Docs | 複製資料至 docs**: The web page expects data to be inside the `/docs/data` directory. Copy the fetched data over.
    *   網頁需要讀取 `/docs/data` 裡的資料，請將剛抓取的數據複製過去。
    ```bash
    # On macOS/Linux | 在 macOS/Linux 上
    mkdir -p docs/data && cp -r data/* docs/data/

    # On Windows (PowerShell) | 在 Windows (PowerShell) 上
    if (-not (Test-Path -Path docs/data)) { New-Item -ItemType Directory -Path docs/data }; Copy-Item -Path data\* -Destination docs\data -Recurse
    ```
3.  **Start a Web Server | 啟動網頁伺服器**: You need a local web server to view the `index.html` file correctly. The easiest way is using Python's built-in server. From the project's root directory, run:
    *   您需要一個本地網頁伺服器才能正確瀏覽 `index.html`。最簡單的方式是使用 Python 內建的伺服器。請在專案的根目錄下執行：
    ```bash
    # For Python 3 | 適用於 Python 3
    python -m http.server 8000
    ```
4.  **View in Browser | 在瀏覽器中查看**: Open your web browser and navigate to `http://localhost:8000/docs/`.
    *   打開您的瀏覽器並前往 `http://localhost:8000/docs/`。

---

## 📊 Data Update Schedule | 資料更新排程

GitHub Actions runs automatically:
- **Every Hour**: Runs on the hour (`0 * * * *`), 24/7.
- **On Push**: Whenever code is pushed to the `main` or `master` branch.
- **Manual Trigger**: Via the **Actions** tab in your GitHub repository.

---

## ⚠️ Disclaimer | 免責聲明
This tool is for **educational purposes only**. Not financial advice. Always do your own research before making investment decisions.
本系統僅供**教育用途**，不構成任何投資建議。投資有風險，請自行判斷。

## 📜 License | 授權
MIT License.

---
Made with ❤️ for the trading community
