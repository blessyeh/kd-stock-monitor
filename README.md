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

The concrete filter reasons (which checks passed vs. flagged caution) are shown directly on each alert card in the dashboard.

### 📊 Per-Stock Institutional Flow (個股外資買賣超)
Beyond the market-wide foreign/investment-trust net buy-sell already covered in Taiwan Chip Flow Indicators (below), each individually-tracked TW ticker now gets its own foreign/investment-trust/dealer net buy-sell in shares, via FinMind's `TaiwanStockInstitutionalInvestorsBuySell` dataset (works uniformly for TWSE, TPEx/OTC, and ETFs). This feeds directly into the KD Alert Filters above as an additional confirming signal: a 3-day cumulative foreign net buy during an oversold reading, or a 3-day cumulative foreign net sell during an overbought reading, can independently confirm the alert even when the MA/Bollinger filters don't — smart-money accumulation/distribution in a specific stock is a real signal on its own, not just a byproduct of price action. Shown on every TW stock card in the dashboard.

### 🔒 Manage Watchlist (owner-only add/remove)
The dashboard has a "管理監控股票" panel for adding or removing a monitored stock — restricted to the repo owner, with **no credentials of any kind stored in or entered into the site**. Submitting the form opens a pre-filled GitHub "New Issue" (`[監控股票申請] ...`) instead of calling any API directly. A dedicated workflow (`.github/workflows/stock-request.yml`) is the actual gatekeeper: it only ever runs for issues opened by `github.repository_owner` — a request opened by anyone else is left completely untouched (no comment, no config change). When it does run, it parses the issue body, updates `config.json` via `scripts/apply_stock_request.py`, commits, and comments + closes the issue with the result; the push then triggers the normal hourly update workflow to fetch the new/removed ticker within minutes. This design deliberately avoids storing a GitHub token in the browser — an earlier PAT-in-`localStorage` version of this idea was removed for exactly that risk (see commit `53fc74560`).

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

### 🚧 Roadmap | 尚待開發
- **CPI/PCE, Non-Farm Payrolls & Unemployment Rate | CPI/PCE、非農就業與失業率**: Fetchable for free via FRED's no-key CSV endpoint, but these are monthly releases (not continuous prices) — they need a different "latest value + release date + countdown" UI treatment rather than the hourly ticker-card style, so they're deferred rather than shoehorned in.
   *   可透過 FRED 免金鑰 CSV 端點免費取得，但這些是月度公布數據（非連續價格），需要另一種「最新公布值+公布日期+倒數」的呈現方式，而非現有的每小時卡片樣式，因此先不做。
- **ISM Manufacturing PMI**: Not planned — ISM revoked FRED's license to redistribute this data in 2016, and there's no reliable free official source anymore (real-time PMI is generally paywalled via Trading Economics/Bloomberg).
   *   不在計畫內——ISM 已於 2016 年收回 FRED 的資料授權，目前沒有可靠的官方免費來源（即時 PMI 多半來自付費資料商）。
- **Git repository housekeeping | Git 倉庫維護**: `docs/data/` was added to `.gitignore` (it's a deploy-time build artifact and shouldn't be version-controlled), but the already-tracked copy still needs a one-time `git rm -r --cached docs/data` to actually stop tracking it.
   *   `docs/data/` 已加入 `.gitignore`（這是部署時才產生的建置產物，不該進版控），但既有已追蹤的檔案還需要手動跑一次 `git rm -r --cached docs/data` 才會真正停止追蹤。

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

具體套用了哪些濾網條件（通過與提醒的項目）會直接顯示在儀表板的每一則警示卡片上。

### 📊 個股外資買賣超
除了台股籌碼面指標中原有的「大盤整體」外資／投信買賣超之外，現在每一檔個別追蹤的台股標的也會有自己的外資／投信／自營商買賣超（股數），資料來源為 FinMind 的 `TaiwanStockInstitutionalInvestorsBuySell`（上市、上櫃、ETF 皆適用）。這項資料會直接納入上方「KD 警示多重濾網」作為額外的確認訊號：超賣情境下若近 3 日外資累計買超、或超買情境下若近 3 日外資累計賣超，即使 MA／布林通道濾網未能確認，也能獨立確認該警示——個股外資的買賣動向本身就是有意義的訊號，不只是股價波動的附屬產物。此資料會顯示在每一張台股個股卡片上。

### 🔒 管理監控股票（僅限擁有者）
儀表板上有一個「管理監控股票」面板，可以新增或移除監控的股票——僅限本專案擁有者本人操作，且**網站本身不會儲存或要求任何帳號密碼、Token**。送出表單時會開啟一個預先填好內容的 GitHub「New Issue」，而不是直接呼叫任何 API。真正的權限判斷在一個獨立的 GitHub Action（`.github/workflows/stock-request.yml`）：只有當 Issue 是由 `github.repository_owner` 本人開啟時才會執行，其他人開的申請完全不會有任何反應（不留言、不變更設定）。當它真的執行時，會解析 Issue 內容、透過 `scripts/apply_stock_request.py` 更新 `config.json`、提交變更，並在 Issue 留言告知結果後自動關閉——推送變更後會自動觸發每小時的資料更新流程，幾分鐘內就能看到新增/移除的標的生效。這個設計刻意避開了在瀏覽器儲存 GitHub Token 的做法——先前曾經有過把 PAT 存在 `localStorage` 的版本，因為風險考量已經移除（見 commit `53fc74560`）。

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

### 🚧 尚待開發
- **CPI/PCE、非農就業與失業率**：可透過 FRED 免金鑰 CSV 端點免費取得，但這些是月度公布數據（非連續價格），需要另一種「最新公布值+公布日期+倒數」的呈現方式，而非現有的每小時卡片樣式，因此先不做。
- **ISM 製造業 PMI**：不在計畫內——ISM 已於 2016 年收回 FRED 的資料授權，目前沒有可靠的官方免費來源（即時 PMI 多半來自付費資料商）。
- **Git 倉庫維護**：`docs/data/` 已加入 `.gitignore`（這是部署時才產生的建置產物，不該進版控），但既有已追蹤的檔案還需要手動跑一次 `git rm -r --cached docs/data` 才會真正停止追蹤。

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
