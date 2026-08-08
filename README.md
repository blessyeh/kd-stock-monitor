# 📊 KD Stock Monitor | 股票 KD 指標監控系統

[English](#english) | [繁體中文](#繁體中文)

---

<a name="english"></a>
## 🌐 English Description

A GitHub-powered stock monitoring system that tracks KD (Stochastic Oscillator) indicators for Taiwan and US stocks. Features automatic **hourly** data updates and a web dashboard deployed on GitHub Pages.

### ✨ Features
- 📈 **KD Indicator Tracking**: Calculates 9-day Stochastic Oscillator (KD) for all monitored stocks.
- 🔔 **Smart Alerts**: Automatic notifications when KD ≥ 80 (overbought) or ≤ 20 (oversold).
- 🇹🇼 **Taiwan Stocks**: Supports TWSE stocks (e.g., 0050.TW, 2330.TW).
- 🇺🇸 **US Stocks**: Supports NYSE/NASDAQ stocks (e.g., AAPL, TSLA).
- 🌐 **Web Dashboard**: Interactive dashboard with charts and real-time data.
- 🌍 **Global Macro Indicators**: VIX, US 10Y yield, DXY, Bitcoin, WTI Crude Oil, and Gold.
- 🇹🇼 **Taiwan Chip Flow**: Foreign/investment-trust net buy-sell, margin & short balances, USD/TWD — sourced from TWSE's free open-data API.
- 🎯 **Signal Confluence Model**: Cross-validates macro + chip-flow indicators against a top/bottom turning-point framework (see below).
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

### 🇹🇼 Taiwan Chip Flow Indicators | 台股籌碼面指標
Sourced from TWSE's official free open-data endpoints (no API key required). These are End-of-Day figures — posted roughly 15:00–19:00 Taipei time — not intraday ticks, so the dashboard shows which trading day each value is actually for.
來自台灣證交所 (TWSE) 官方免費開放資料 (無需 API 金鑰)。這些是每日收盤後才會公布的資料（約台北時間 15:00–19:00），並非即時報價，因此儀表板會標示每個數值實際對應的交易日。

1. **Foreign / Investment Trust Net Buy-Sell | 外資 / 投信買賣超**: Market-wide net NT$ flow from the daily 三大法人買賣金額統計表 (BFI82U). Foreign investors dominate TWSE market cap, so sustained buying/selling drives the index's medium-term direction; 投信 flows matter most for small/mid caps and ETF constituents.
   *   來自「三大法人買賣金額統計表」的全市場淨買賣金額。外資占台股市值比重極高，是加權指數中長期方向的主要驅動力；投信資金對中小型股與 ETF 成分股影響力較大。
2. **Margin / Short Balance & Ratio | 融資融券餘額與資券比**: From the daily 信用交易統計 (MI_MARGN). Margin balance reflects retail leverage; short balance reflects bearish bets. A sudden, sharp drop in margin balance ("融資斷頭") is one of the most objective signs of forced retail capitulation.
   *   來自「信用交易統計」。融資餘額代表散戶槓桿多頭力道，融券餘額代表空頭部位。融資餘額單日大減（俗稱「融資斷頭」）是散戶籌碼洗淨最客觀的訊號之一。
3. **USD/TWD Exchange Rate | 新台幣匯率**: A leading/coincident indicator for foreign capital flows — TWD appreciation typically accompanies foreign inflows, sustained depreciation typically accompanies foreign capital leaving.
   *   外資進出台股的領先/同步指標。新台幣升值通常伴隨外資匯入，持續貶值則通常伴隨外資撤出。

### 🎯 Signal Confluence Model | 訊號共振：大盤轉折模型
No single macro or chip indicator is trusted in isolation — this model (`src/signal_confluence.py`) only flags a potential turning point when **multiple independent conditions agree**, cross-validating global macro flows, TWD, and TW-specific chip flow.
不單看任何單一指標——這個模型（`src/signal_confluence.py`）只有在**多項獨立條件同時出現共振**時才會標示可能的轉折點，交叉驗證全球宏觀資金、匯率與台股籌碼面。

**Top structure / hedge-trigger signals | 頂部結構與避險啟動訊號** (risk rising):
- Macro capital drain: DXY breaks above its recent high **and** US 10Y yield rises quickly. | 宏觀資金抽離：DXY 突破前高，且美債 10Y 快速攀升。
- TWD depreciation: sustained weakening or breaking a round-number level. | 匯率表態：新台幣連續走貶或貶破整數關卡。
- Foreign spot+futures dual short *(spot leg only — see Roadmap)*. | 外資期現貨雙空 *(僅現貨那一半，見下方尚待開發)*。
- Retail holding the bag: foreign selling while margin balance keeps rising *(missing the Put/Call Ratio leg — see Roadmap)*. | 籌碼過度樂觀/散戶接刀：外資倒貨同時融資餘額不退 *(缺選擇權 P/C Ratio 那一半，見下方尚待開發)*。

**Bottom turning point / add-position signals | 底部轉折與加碼訊號** (crisis clearing):
- VIX extreme reversal: spikes above 30 then rolls over. | 恐慌極值反轉：VIX 飆高後見頂回落。
- Retail capitulation: a sharp single-day drop in margin balance ("融資斷頭"). | 散戶投降：融資餘額斷頭式大減。
- FX stabilizing + foreign spot flow reversal *(futures short-covering leg not available — see Roadmap)*. | 匯率止穩、外資現貨轉買 *(缺期貨空單回補那一半，見下方尚待開發)*。

Conditions that can only verify half of the original logic (because the TAIFEX futures/options leg isn't wired up yet) are flagged **"部分驗證" (partially verified)** in the UI, distinct from fully-verified conditions.
只能驗證原始邏輯一半的條件（因為 TAIFEX 期貨/選擇權資料還沒接上），畫面上會標示**「部分驗證」**，跟完整驗證的條件明確區分。

⚠️ Per the model's own design intent: this is a reference point for large lump-sum entries or pausing a chase-the-rally purchase — **not** a signal for frequent trading or shorting. If you're running a DCA strategy on a broad-market ETF (e.g., 0050), letting short-term futures/chip noise trigger "dynamic hedging" typically costs more (in hedging losses when the read turns out wrong) than it saves.
⚠️ 依照模型本身的設計初衷：這是單筆大額加碼或停止追高的參考依據，**並非**頻繁進出或放空訊號。若本身在對大盤型 ETF（如 0050）執行定期定額策略，讓短線期貨/籌碼雜訊觸發「動態避險」，一旦判斷錯誤，避險成本通常比它省下的還多。

### 🚧 Roadmap | 尚待開發
- **TAIFEX foreign futures net short position | 外資台指期未平倉淨部位**: The official TAIFEX OpenAPI endpoint exists, but its response schema hasn't been verified against real data yet — not wired up to avoid silently-wrong parsing on a live dashboard.
   *   TAIFEX 官方 OpenAPI 確實有這支端點，但尚未能驗證實際回應格式，為避免在正式站上悄悄解析錯誤，暫不串接。
- **Options Put/Call Ratio | 選擇權 Put/Call Ratio**: Same situation — endpoint exists on TAIFEX OpenAPI, schema unverified.
   *   同上，TAIFEX OpenAPI 有此端點，但格式尚未驗證。
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
- 🔔 **智能警示**：當 KD ≥ 80 (超買) 或 ≤ 20 (超賣) 時自動發出提醒。
- 🇹🇼 **台股支援**：支援台股代碼 (如 0050.TW, 2330.TW)。
- 🇺🇸 **美股支援**：支援美股代碼 (如 AAPL, TSLA)。
- 🌐 **網頁儀表板**：提供圖表與即時數據的互動式介面。
- 🌍 **全球宏觀指標**：VIX、美債 10Y、美元指數、比特幣、原油 (WTI)、黃金。
- 🇹🇼 **台股籌碼面**：外資/投信買賣超、融資融券餘額、新台幣匯率，資料來源為 TWSE 官方免費開放資料。
- 🎯 **訊號共振模型**：交叉驗證宏觀指標與台股籌碼面，判斷大盤頂部/底部轉折（詳見下方說明）。
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

### 🌐 宏觀指標
1. **VIX 恐慌指數**: 衡量市場波動度與恐慌情緒。高 VIX (>30) 通常代表恐慌，可能是分批買點。
2. **美債 10 年期收益率**: 無風險利率的基準。收益率上升會對股市估值造成壓力，尤其是科技股。
3. **美元指數**: 衡量美元強度。強勢美元通常會對新興市場與大宗商品價格產生壓力。
4. **比特幣**: 通常被視為高風險資產的代表。其趨勢反映了市場對風險的整體偏好程度。
5. **原油 (WTI)**: 生產與運輸成本的代表。油價飆升會引發輸入型通膨，壓抑企業利潤，並迫使央行維持高利率。
6. **黃金**: 對沖地緣政治風險與法幣貶值的工具，可與比特幣（高風險偏好）互補觀察市場情緒。

### 🇹🇼 台股籌碼面指標
資料來源為台灣證交所 (TWSE) 官方免費開放資料，無需 API 金鑰。這些是每日收盤後才會公布的資料（約台北時間 15:00–19:00），並非即時報價，儀表板會標示每個數值實際對應的交易日。

1. **外資 / 投信買賣超**：來自「三大法人買賣金額統計表」的全市場淨買賣金額。外資占台股市值比重極高，是加權指數中長期方向的主要驅動力；投信資金對中小型股與 ETF 成分股影響力較大。
2. **融資融券餘額與資券比**：來自「信用交易統計」。融資餘額代表散戶槓桿多頭力道，融券餘額代表空頭部位。融資餘額單日大減（俗稱「融資斷頭」）是散戶籌碼洗淨最客觀的訊號之一。
3. **新台幣匯率**：外資進出台股的領先/同步指標。新台幣升值通常伴隨外資匯入，持續貶值則通常伴隨外資撤出。

### 🎯 訊號共振：大盤轉折模型
不單看任何單一指標——這個模型（`src/signal_confluence.py`）只有在**多項獨立條件同時出現共振**時才會標示可能的轉折點，交叉驗證全球宏觀資金、匯率與台股籌碼面。

**頂部結構與避險啟動訊號**（風險升高）：
- 宏觀資金抽離：DXY 突破前高，且美債 10Y 快速攀升。
- 匯率表態：新台幣連續走貶或貶破整數關卡。
- 外資期現貨雙空*（僅現貨那一半，見下方尚待開發）*。
- 籌碼過度樂觀/散戶接刀：外資倒貨同時融資餘額不退*（缺選擇權 P/C Ratio 那一半，見下方尚待開發）*。

**底部轉折與加碼訊號**（危機解除）：
- 恐慌極值反轉：VIX 飆高後見頂回落。
- 散戶投降：融資餘額斷頭式大減。
- 匯率止穩、外資現貨轉買*（缺期貨空單回補那一半，見下方尚待開發）*。

只能驗證原始邏輯一半的條件（因為 TAIFEX 期貨/選擇權資料還沒接上），畫面上會標示**「部分驗證」**，跟完整驗證的條件明確區分。

⚠️ 依照模型本身的設計初衷：這是單筆大額加碼或停止追高的參考依據，**並非**頻繁進出或放空訊號。若本身在對大盤型 ETF（如 0050）執行定期定額策略，讓短線期貨/籌碼雜訊觸發「動態避險」，一旦判斷錯誤，避險成本通常比它省下的還多。

### 🚧 尚待開發
- **外資台指期未平倉淨部位**：TAIFEX 官方 OpenAPI 確實有這支端點，但尚未能驗證實際回應格式，為避免在正式站上悄悄解析錯誤，暫不串接。
- **選擇權 Put/Call Ratio**：同上，TAIFEX OpenAPI 有此端點，但格式尚未驗證。
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
git clone https://github.com/jack-lee2022/kd-stock-monitor.git
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
