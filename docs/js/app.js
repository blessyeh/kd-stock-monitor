/**
 * Main Application Module - KD Stock Monitor Dashboard
 * Dark Theme Edition
 */

// Global state
let currentFilter = 'all';

/**
 * Render the small "▲+1.23%" / "▼-0.45%" line under a macro card's value,
 * showing day-over-day change so it's visible without hovering (a tooltip
 * alone isn't usable on mobile / touch devices).
 */
function renderMacroChange(elId, changePct) {
    const el = document.getElementById(elId);
    if (!el) return;
    if (changePct === null || changePct === undefined || isNaN(changePct)) {
        el.textContent = '-';
        el.className = 'text-[10px] leading-tight text-dark-text2';
        return;
    }
    const colorClass = changePct >= 0 ? 'text-kd-red' : 'text-kd-green';
    const arrow = changePct >= 0 ? '▲' : '▼';
    const sign = changePct >= 0 ? '+' : '';
    el.className = `text-[10px] leading-tight ${colorClass}`;
    el.textContent = `${arrow} ${sign}${changePct.toFixed(2)}%`;
}

/**
 * Explanation text for the "ⓘ" info-trigger icons scattered across the
 * dashboard. Kept as tap-to-open popovers (see initInfoPopovers()) instead
 * of hover tooltips/title attributes, because title tooltips don't fire on
 * touch devices — most of this dashboard's traffic is mobile.
 */
const INFO_TEXT = {
    foreign_net: {
        title: '外資買賣超',
        body: '外資（外國機構投資人）當日在台股集中市場的買賣超金額（億元）。正值代表買超（資金流入台股),負值代表賣超（資金流出)。外資規模龐大，是觀察台股資金動向最重要的指標之一。'
    },
    trust_net: {
        title: '投信買賣超',
        body: '投信（國內基金）當日買賣超金額（億元)。資金規模比外資小很多，但常被視為「內資」對台股中小型股態度的指標，尤其在外資大幅賣超時，投信是否進場承接常受市場關注。'
    },
    margin_balance: {
        title: '融資餘額',
        body: '一般散戶以融資（向券商借錢）買進股票的未平倉張數。融資餘額持續增加，代表散戶追價意願升溫，但也代表槓桿風險升高；股市重挫時常伴隨融資餘額大幅減少（俗稱融資斷頭）。'
    },
    margin_short_ratio: {
        title: '資券比',
        body: '融券餘額 ÷ 融資餘額 的比值（%），用來衡量市場做空力道相對做多力道的強度。比值異常偏高，有時代表放空籌碼集中，若股價續漲可能引發軋空（逼空）行情；但這只是輔助觀察指標，不宜單獨作為買賣依據。'
    },
    usdtwd: {
        title: '新台幣匯率',
        body: '美元兌新台幣匯率（USD/TWD）。新台幣升值（數字下降）通常伴隨外資匯入買進台股；新台幣貶值（數字上升）則常見於外資匯出、資金退出台股的階段。'
    },
    foreign_futures_net: {
        title: '外資期貨淨部位',
        body: '外資在台指期貨的未平倉淨部位（口數)。正值為淨多單（外資看多台股後市走勢),負值為淨空單（看空)。由於台指期貨具槓桿與領先性，常被視為外資對大盤短期方向的態度指標。'
    },
    put_call_ratio: {
        title: '選擇權 P/C 比',
        body: '賣權（Put）未平倉量 ÷ 買權（Call）未平倉量的比值（%）。數值愈高，代表市場避險或看跌需求愈重；數值愈低，代表市場偏樂觀。P/C 比出現極端值時，常被當作反向指標參考（過度悲觀或過度樂觀，都可能醞釀反轉），但仍須搭配其他指標判讀。'
    },
    night_session: {
        title: '台指期夜盤',
        body: '台指期夜盤跳空幅度，與前一交易日日盤收盤價比較。這是收盤後回溯性資料（約台北時間16:30才更新，隨當天籌碼面資料一起發布），並非盤中即時報價，主要用來輔助觀察隔夜國際盤氣氛，判斷隔天台股開盤可能的跳空方向與幅度。'
    },
    market_news: {
        title: '重大財經新聞',
        body: '每小時自動從 Yahoo奇摩股市（tw.stock.yahoo.com）財經新聞頁面抓取的繁體中文頭條，涵蓋台股盤勢、美股、陸港股、黃金、外匯等大盤／宏觀新聞，點擊可開啟原始新聞頁面。這是本專案資料來源中最容易失效的一項——Yahoo 並未提供正式的新聞 API，抓取邏輯依賴新聞頁面的網址格式，若 Yahoo 改版可能暫時抓不到新聞（此時此區塊會顯示暫無新聞，不影響其他功能）。'
    },
    signal_confluence: {
        title: '訊號共振：大盤轉折觀察',
        body: '整合多項技術面與籌碼面條件（如 VIX 反轉、融資斷頭、外資回補空單、費半/那斯達克跌破支撐、美債殖利率急升等），尋找台股大盤「可能出現短線頂部或底部」的訊號共振時刻。當愈多條件同時成立，代表出現轉折的機率愈高——但這是機率參考工具，並非即時買賣訊號，也不是放空建議，請勿單獨依賴、更不建議因短線訊號打斷既有的定期定額投資紀律。'
    },
    market_regime: {
        title: '市場狀態 (Market Regime)',
        body: '依 TAIEX 相對長天期均線的位置與斜率、VIX 是否急升/見頂回落、外資資金流向是否反轉，將目前大盤狀態分類為「多頭趨勢」「多頭回檔」「空頭趨勢」「恐慌急殺」「築底回穩」五種之一。同樣的訊號（例如個股 KD 超賣）在不同市場狀態下代表的意義不同：多頭回檔時的超賣通常是加碼機會，空頭趨勢或恐慌時的超賣則可能只是持續破底的開始。本專案的個股警示會依目前市場狀態調整確認門檻（詳見警示卡片內的說明），但這仍是規則式分類，並非對未來走勢的預測。'
    },
    tsmc_analysis: {
        title: '台積電 (2330) 投資決策分析',
        body: '台積電是本站監控名單中最大的持股，其股價通常提前反應「未來獲利預期的變化」而非落後反應已公布的財報，因此不適合單純用 KD/MACD 等技術指標判斷。此模型把 2330 拆成 10 個構面（各自獨立加總，滿分100）：營收動能15分、毛利率/EPS趨勢10分、法說會財測指引15分、技術趨勢15分（均線多頭排列）、動能綜合10分（KD/RSI/MACD取平均而非加總，避免三個高度相關指標重複計分）、相對強弱10分（相對台股/費半/那斯達克）、外資籌碼10分、ADR溢折價5分、大盤環境5分（引用市場狀態模組）、估值5分（本益比歷史百分位）。三種買點設定（基本面回撤／趨勢突破／恐慌反轉）皆同時要求基本面門檻與市場時機觸發，避免「好公司壞價格」或「純粹接刀」。最大限制：分析師市場共識預期與台積電正式財測指引數字，目前沒有免費、可自動抓取的資料源，法說會指引的部分是人工每季更新（data/tsmc_guidance.json），並非即時抓取；本分數同樣尚未經過歷史回測驗證統計勝率。'
    },
    kd_state: {
        title: 'KD 狀態 (KD State)',
        body: '比單純「超買/超賣」更細緻的 KD 判讀，同時參考昨日的 K/D 位置：黃金交叉／死亡交叉＝K、D 今日剛交叉；超買中·動能未歇＝K-D 差距仍在擴大，多頭動能尚未停歇（此時的「超買」較可能只是鈍化，非賣出訊號）；超買轉弱＝K-D 差距開始收斂，動能停滯，較可能是真正的高點；超賣反轉／超賣回升中＝同樣邏輯用在低檔。多頭/空頭動能則是 K、D 未進入極端區間時的方向判斷。這仍是規則式分類，並非預測。'
    },
    market_regime: {
        title: '市場狀態 (Market Regime)',
        body: '將「訊號共振」使用的同一批市場資料，重新拆解為五個面向（總經 Macro／籌碼 Chip Flow／衍生性商品 Derivative／技術面 Technical／情緒面 Sentiment），各自給予權重加總成 0-100 分的「頂部風險分數」與「底部佈局分數」，取代原本非黑即白的「N/5 項共振」表示法，讓強弱程度可以比較。務必注意：這是人工設定權重的規則式評分，並非經過歷史資料回測、驗證過勝率的統計模型——「82分」的意思是「目前有82%權重的已知條件成立」，不是「82%機率會反轉」。事後績效追蹤與回測是規劃中的下一階段功能。'
    }
};

/**
 * Wire up the info-trigger icons (see INFO_TEXT above) to open/close the
 * shared #info-modal-backdrop popover. Uses event delegation so it also
 * covers any info-trigger icons rendered dynamically later.
 */
function initInfoPopovers() {
    const backdrop = document.getElementById('info-modal-backdrop');
    const titleEl = document.getElementById('info-modal-title');
    const bodyEl = document.getElementById('info-modal-body');
    const closeBtn = document.getElementById('info-modal-close');
    if (!backdrop || !titleEl || !bodyEl) return;

    function open(key) {
        const info = INFO_TEXT[key];
        if (!info) return;
        titleEl.textContent = info.title;
        bodyEl.textContent = info.body;
        backdrop.classList.remove('hidden');
    }
    function close() {
        backdrop.classList.add('hidden');
    }

    document.addEventListener('click', (e) => {
        const trigger = e.target.closest('.info-trigger');
        if (trigger) {
            e.preventDefault();
            e.stopPropagation();
            open(trigger.dataset.info);
            return;
        }
        if (e.target === backdrop) close();
    });
    if (closeBtn) closeBtn.addEventListener('click', close);

    const manageBackdrop = document.getElementById('manage-stocks-backdrop');
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            close();
            closeManageStocksModal();
        }
    });
    if (manageBackdrop) {
        manageBackdrop.addEventListener('click', (e) => {
            if (e.target === manageBackdrop) closeManageStocksModal();
        });
    }
}

/**
 * Manage Watchlist (新增/移除監控股票) — repo-owner-only via GitHub Issues.
 *
 * This dashboard is a static GitHub Pages site with no backend, so there's
 * no server to check "is this really the owner?" against. The site itself
 * never asks for or stores any credential (a PAT-in-localStorage version of
 * this was tried once and removed for exactly that risk). Instead, this
 * just opens a pre-filled GitHub "New Issue" — GitHub's own login state
 * decides who's allowed to open it as themselves, and
 * .github/workflows/stock-request.yml only ever applies the change if the
 * issue's author is github.repository_owner. Anyone else's submission
 * creates an inert issue that the automation silently ignores.
 */
const STOCK_REQUEST_REPO = 'blessyeh/kd-stock-monitor';

function openManageStocksModal() {
    const backdrop = document.getElementById('manage-stocks-backdrop');
    if (!backdrop) return;
    populateRemoveStockSelect();
    backdrop.classList.remove('hidden');
}

function closeManageStocksModal() {
    const backdrop = document.getElementById('manage-stocks-backdrop');
    if (backdrop) backdrop.classList.add('hidden');
}

function switchManageStocksTab(tab) {
    const addPanel = document.getElementById('manage-panel-add');
    const removePanel = document.getElementById('manage-panel-remove');
    const addTab = document.getElementById('manage-tab-add');
    const removeTab = document.getElementById('manage-tab-remove');
    const activeClass = ['border-accent', 'text-white', 'font-semibold'];
    const inactiveClass = ['border-transparent', 'text-dark-text2'];

    if (tab === 'add') {
        addPanel.classList.remove('hidden');
        removePanel.classList.add('hidden');
        addTab.classList.add(...activeClass);
        addTab.classList.remove(...inactiveClass);
        removeTab.classList.add(...inactiveClass);
        removeTab.classList.remove(...activeClass);
    } else {
        removePanel.classList.remove('hidden');
        addPanel.classList.add('hidden');
        removeTab.classList.add(...activeClass);
        removeTab.classList.remove(...inactiveClass);
        addTab.classList.add(...inactiveClass);
        addTab.classList.remove(...activeClass);
    }
}

function populateRemoveStockSelect() {
    const select = document.getElementById('remove-stock-select');
    if (!select) return;
    const stocks = DataManager.getAllStocks();
    if (!stocks.length) {
        select.innerHTML = '<option value="">（尚無資料）</option>';
        return;
    }
    select.innerHTML = stocks
        .map(s => `<option value="${s.symbol}">${s.symbol} - ${s.name} (${s.market})</option>`)
        .join('');
}

/**
 * Builds a GitHub "New Issue" URL pre-filled with a machine-parseable body.
 * See scripts/apply_stock_request.py for the exact format this must match
 * (an HTML-comment marker line, then ACTION/SYMBOL/NAME/MARKET key:value
 * lines) — the two are intentionally kept in sync manually since this is a
 * tiny, stable contract.
 */
function buildStockRequestIssueUrl(action, symbol, name, market) {
    const title = action === 'add'
        ? `[監控股票申請] 新增 ${symbol}`
        : `[監控股票申請] 移除 ${symbol}`;
    const bodyLines = ['<!-- stock-request -->', `ACTION: ${action}`, `SYMBOL: ${symbol}`];
    if (action === 'add') {
        bodyLines.push(`NAME: ${name}`, `MARKET: ${market}`);
    }
    const params = new URLSearchParams({
        title,
        body: bodyLines.join('\n'),
        labels: 'stock-request'
    });
    return `https://github.com/${STOCK_REQUEST_REPO}/issues/new?${params.toString()}`;
}

function submitAddStockRequest() {
    const symbol = document.getElementById('add-stock-symbol').value.trim();
    const name = document.getElementById('add-stock-name').value.trim();
    const market = document.getElementById('add-stock-market').value;

    if (!symbol || !name) {
        alert('請填寫股票代碼與名稱');
        return;
    }

    const url = buildStockRequestIssueUrl('add', symbol, name, market);
    window.open(url, '_blank');
    closeManageStocksModal();
}

function submitRemoveStockRequest() {
    const select = document.getElementById('remove-stock-select');
    const symbol = select ? select.value : '';

    if (!symbol) {
        alert('請選擇要移除的股票');
        return;
    }

    const url = buildStockRequestIssueUrl('remove', symbol, '', '');
    window.open(url, '_blank');
    closeManageStocksModal();
}

/**
 * Initialize the application
 */
document.addEventListener('DOMContentLoaded', async () => {
    console.log('KD Stock Monitor - Initializing...');

    // Load data
    await DataManager.loadData();

    // Initialize UI
    updateStats();
    updateTaiexSection();
    renderRegimeBadge();
    renderMarketNews();
    updateChipStats();
    renderSignalScore();
    renderSignalConfluence();
    renderTsmcAnalysis();
    renderStockGrid();
    renderAlertHistory();
    updateLastUpdated();
    initInfoPopovers();

    // Initialize ECharts
    StockChart.init('stock-chart');
    populateChartSelect();

    console.log('KD Stock Monitor - Ready');
});

/**
 * Update statistics cards
 */
function updateStats() {
    try {
        const summary = DataManager.getSummary() || { overbought_count: 0, oversold_count: 0 };
        const allStocks = DataManager.getAllStocks() || [];
        const alerts = DataManager.getAlerts() || [];
        const today = new Date().toISOString().split('T')[0];
        const todayAlerts = alerts.filter(a => a && a.date === today);

        const totalStocksEl = document.getElementById('total-stocks');
        if (totalStocksEl) totalStocksEl.textContent = allStocks.length;

        const overboughtEl = document.getElementById('overbought-count');
        if (overboughtEl) overboughtEl.textContent = summary.overbought_count || 0;

        const oversoldEl = document.getElementById('oversold-count');
        if (oversoldEl) oversoldEl.textContent = summary.oversold_count || 0;

        const todayAlertsEl = document.getElementById('today-alerts');
        if (todayAlertsEl) todayAlertsEl.textContent = todayAlerts.length;

        // Update Macro Stats
        if (summary.macro) {
            const macro = summary.macro;

            // 1. Fear & Greed (Actually VIX Index)
            const fngEl = document.getElementById('macro-fng');
            if (fngEl && macro.fear_greed && macro.fear_greed.value !== null) {
                const val = macro.fear_greed.value;
                let colorClass = 'text-gray-400';

                // VIX: Higher is more fearful (Red), Lower is more calm (Green)
                if (val >= 40) colorClass = 'text-red-500 font-extrabold';
                else if (val >= 30) colorClass = 'text-red-400';
                else if (val >= 25) colorClass = 'text-orange-400';
                else if (val >= 20) colorClass = 'text-yellow-400';
                else if (val < 15) colorClass = 'text-green-500';
                else colorClass = 'text-green-400';

                fngEl.className = `font-bold text-lg ${colorClass}`;
                fngEl.textContent = val.toFixed(2);
                fngEl.title = `VIX 恐慌指數: ${val.toFixed(2)}`;
                renderMacroChange('macro-fng-chg', macro.fear_greed.change_pct);
            }

            // 2. US 10Y
            const us10yEl = document.getElementById('macro-us10y');
            if (us10yEl && macro.us10y) {
                const val = macro.us10y.value || 0;
                const change = macro.us10y.change || 0;
                const colorClass = change >= 0 ? 'text-kd-red' : 'text-kd-green';
                us10yEl.className = `font-bold text-lg ${colorClass}`;
                us10yEl.textContent = `${val.toFixed(2)}%`;
                renderMacroChange('macro-us10y-chg', macro.us10y.change_pct);
            }

            // 3. DXY
            const dxyEl = document.getElementById('macro-dxy');
            if (dxyEl && macro.dxy) {
                const val = macro.dxy.value || 0;
                const change = macro.dxy.change || 0;
                const colorClass = change >= 0 ? 'text-kd-red' : 'text-kd-green';
                dxyEl.className = `font-bold text-lg ${colorClass}`;
                dxyEl.textContent = val.toFixed(2);
                renderMacroChange('macro-dxy-chg', macro.dxy.change_pct);
            }

            // 4. Bitcoin
            const btcEl = document.getElementById('macro-btc');
            if (btcEl && macro.btc) {
                const val = macro.btc.value || 0;
                const change = macro.btc.change_pct || 0;
                const colorClass = change >= 0 ? 'text-kd-green' : 'text-kd-red';
                const formattedPrice = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(val);
                btcEl.className = `font-bold text-lg ${colorClass}`;
                btcEl.textContent = formattedPrice;
                renderMacroChange('macro-btc-chg', macro.btc.change_pct);
            }

            // 5. WTI Crude Oil
            const oilEl = document.getElementById('macro-oil');
            if (oilEl && macro.oil && macro.oil.value !== null) {
                const val = macro.oil.value;
                const changePct = macro.oil.change_pct || 0;
                const colorClass = changePct >= 0 ? 'text-kd-red' : 'text-kd-green';
                const sign = changePct >= 0 ? '+' : '';
                oilEl.className = `font-bold text-lg ${colorClass}`;
                oilEl.textContent = `$${val.toFixed(2)}`;
                oilEl.title = `WTI 原油: $${val.toFixed(2)} (${sign}${changePct.toFixed(2)}%)`;
                renderMacroChange('macro-oil-chg', macro.oil.change_pct);
            }

            // 6. Gold
            const goldEl = document.getElementById('macro-gold');
            if (goldEl && macro.gold && macro.gold.value !== null) {
                const val = macro.gold.value;
                const changePct = macro.gold.change_pct || 0;
                const colorClass = changePct >= 0 ? 'text-kd-red' : 'text-kd-green';
                const sign = changePct >= 0 ? '+' : '';
                const formattedPrice = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(val);
                goldEl.className = `font-bold text-lg ${colorClass}`;
                goldEl.textContent = formattedPrice;
                goldEl.title = `黃金: ${formattedPrice} (${sign}${changePct.toFixed(2)}%)`;
                renderMacroChange('macro-gold-chg', macro.gold.change_pct);
            }

            // 7. SOX (Philadelphia Semiconductor Index)
            const soxEl = document.getElementById('macro-sox');
            if (soxEl && macro.sox && macro.sox.value !== null) {
                const val = macro.sox.value;
                const changePct = macro.sox.change_pct || 0;
                const colorClass = changePct >= 0 ? 'text-kd-red' : 'text-kd-green';
                const sign = changePct >= 0 ? '+' : '';
                soxEl.className = `font-bold text-lg ${colorClass}`;
                soxEl.textContent = val.toFixed(0);
                soxEl.title = `費城半導體指數: ${val.toFixed(2)} (${sign}${changePct.toFixed(2)}%)`;
                renderMacroChange('macro-sox-chg', macro.sox.change_pct);
            }

            // 8. NDX (Nasdaq 100)
            const ndxEl = document.getElementById('macro-ndx');
            if (ndxEl && macro.ndx && macro.ndx.value !== null) {
                const val = macro.ndx.value;
                const changePct = macro.ndx.change_pct || 0;
                const colorClass = changePct >= 0 ? 'text-kd-red' : 'text-kd-green';
                const sign = changePct >= 0 ? '+' : '';
                ndxEl.className = `font-bold text-lg ${colorClass}`;
                ndxEl.textContent = val.toFixed(0);
                ndxEl.title = `那斯達克100指數: ${val.toFixed(2)} (${sign}${changePct.toFixed(2)}%)`;
                renderMacroChange('macro-ndx-chg', macro.ndx.change_pct);
            }

            // 9. S&P 500
            const sp500El = document.getElementById('macro-sp500');
            if (sp500El && macro.sp500 && macro.sp500.value !== null) {
                const val = macro.sp500.value;
                const changePct = macro.sp500.change_pct || 0;
                const colorClass = changePct >= 0 ? 'text-kd-red' : 'text-kd-green';
                const sign = changePct >= 0 ? '+' : '';
                sp500El.className = `font-bold text-lg ${colorClass}`;
                sp500El.textContent = val.toFixed(0);
                sp500El.title = `標普500指數: ${val.toFixed(2)} (${sign}${changePct.toFixed(2)}%)`;
                renderMacroChange('macro-sp500-chg', macro.sp500.change_pct);
            }
        }
    } catch (e) {
        console.error("Error updating stats:", e);
    }
}

/**
 * Update TW chip-flow (籌碼面) cards.
 * These are End-of-Day TWSE figures (posted ~15:00-19:00 Taipei time), not
 * intraday ticks, so the 'date' shown is which trading day the numbers are
 * actually for — they'll typically only change once per trading day.
 */
function updateChipStats() {
    try {
        const summary = DataManager.getSummary() || {};
        const chip = summary.chip || {};

        const dateEl = document.getElementById('chip-date');
        const anyDate = (chip.foreign_net && chip.foreign_net.date) ||
                         (chip.margin_balance && chip.margin_balance.date);
        if (dateEl) dateEl.textContent = anyDate ? `(資料日期: ${anyDate})` : '';

        // 外資買賣超 (億元) — positive = buy = red, negative = sell = green
        const foreignEl = document.getElementById('chip-foreign');
        if (foreignEl && chip.foreign_net && chip.foreign_net.value !== null && chip.foreign_net.value !== undefined) {
            const val = chip.foreign_net.value;
            const colorClass = val >= 0 ? 'text-kd-red' : 'text-kd-green';
            const sign = val >= 0 ? '+' : '';
            foreignEl.className = `font-bold text-lg mt-1 ${colorClass}`;
            foreignEl.textContent = `${sign}${val.toFixed(1)}億`;
        }
        renderMacroChange('chip-foreign-chg', chip.foreign_net && chip.foreign_net.change_pct);

        // 投信買賣超 (億元)
        const trustEl = document.getElementById('chip-trust');
        if (trustEl && chip.trust_net && chip.trust_net.value !== null && chip.trust_net.value !== undefined) {
            const val = chip.trust_net.value;
            const colorClass = val >= 0 ? 'text-kd-red' : 'text-kd-green';
            const sign = val >= 0 ? '+' : '';
            trustEl.className = `font-bold text-lg mt-1 ${colorClass}`;
            trustEl.textContent = `${sign}${val.toFixed(1)}億`;
        }
        renderMacroChange('chip-trust-chg', chip.trust_net && chip.trust_net.change_pct);

        // 融資餘額 (張) — colored by direction of change vs. previous trading day
        const marginEl = document.getElementById('chip-margin');
        if (marginEl && chip.margin_balance && chip.margin_balance.value !== null && chip.margin_balance.value !== undefined) {
            const val = chip.margin_balance.value;
            const change = chip.margin_balance.change || 0;
            const colorClass = change >= 0 ? 'text-kd-red' : 'text-kd-green';
            const sign = change >= 0 ? '+' : '';
            marginEl.className = `font-bold text-lg mt-1 ${colorClass}`;
            marginEl.textContent = `${(val / 10000).toFixed(1)}萬張`;
            marginEl.title = `融資餘額: ${val.toLocaleString()}張 (${sign}${change.toLocaleString()}張)`;
        }
        renderMacroChange('chip-margin-chg', chip.margin_balance && chip.margin_balance.change_pct);

        // 資券比 (%) — neutral stat, no directional color
        const ratioEl = document.getElementById('chip-ratio');
        if (ratioEl && chip.margin_short_ratio && chip.margin_short_ratio.value !== null && chip.margin_short_ratio.value !== undefined) {
            ratioEl.className = 'font-bold text-lg mt-1 text-dark-text';
            ratioEl.textContent = `${chip.margin_short_ratio.value.toFixed(2)}%`;
        }
        renderMacroChange('chip-ratio-chg', chip.margin_short_ratio && chip.margin_short_ratio.change_pct);

        // 新台幣匯率 (USD/TWD) — same up/down convention as the DXY card
        const twdEl = document.getElementById('chip-twd');
        if (twdEl && chip.usdtwd && chip.usdtwd.value !== null && chip.usdtwd.value !== undefined) {
            const val = chip.usdtwd.value;
            const change = chip.usdtwd.change || 0;
            const colorClass = change >= 0 ? 'text-kd-red' : 'text-kd-green';
            twdEl.className = `font-bold text-lg mt-1 ${colorClass}`;
            twdEl.textContent = val.toFixed(3);
        }
        renderMacroChange('chip-twd-chg', chip.usdtwd && chip.usdtwd.change_pct);

        // 外資期貨淨部位 (口) — positive = net long = red, negative = net short = green
        const futuresEl = document.getElementById('chip-futures');
        if (futuresEl && chip.foreign_futures_net && chip.foreign_futures_net.value !== null && chip.foreign_futures_net.value !== undefined) {
            const val = chip.foreign_futures_net.value;
            const colorClass = val >= 0 ? 'text-kd-red' : 'text-kd-green';
            const sign = val >= 0 ? '+' : '';
            futuresEl.className = `font-bold text-lg mt-1 ${colorClass}`;
            futuresEl.textContent = `${sign}${val.toLocaleString()}口`;
        }
        renderMacroChange('chip-futures-chg', chip.foreign_futures_net && chip.foreign_futures_net.change_pct);

        // 選擇權 Put/Call Ratio (%) — neutral stat, no directional color
        const pcRatioEl = document.getElementById('chip-pcratio');
        if (pcRatioEl && chip.put_call_ratio && chip.put_call_ratio.value !== null && chip.put_call_ratio.value !== undefined) {
            pcRatioEl.className = 'font-bold text-lg mt-1 text-dark-text';
            pcRatioEl.textContent = `${chip.put_call_ratio.value.toFixed(2)}%`;
        }
        renderMacroChange('chip-pcratio-chg', chip.put_call_ratio && chip.put_call_ratio.change_pct);
    } catch (e) {
        console.error("Error updating chip stats:", e);
    }
}

/**
 * Render the 重大財經新聞 (major financial news) panel. Best-effort data —
 * see the panel's info popover (market_news in INFO_TEXT above) for why this
 * can legitimately come back empty sometimes (Yahoo has no public news API;
 * this is scraped, the most fragile source in the pipeline).
 */
function renderMarketNews() {
    const container = document.getElementById('news-list');
    if (!container) return;

    const summary = DataManager.getSummary() || {};
    const news = Array.isArray(summary.news) ? summary.news : [];

    if (news.length === 0) {
        container.innerHTML = '<p class="text-xs text-dark-text2">暫無新聞（資料來源暫時無法取得，不影響其他功能）</p>';
        return;
    }

    container.innerHTML = news.map(item => `
        <a href="${item.url}" target="_blank" rel="noopener noreferrer"
           class="block px-2 py-1.5 rounded hover:bg-white/5 transition">
            <p class="text-sm text-dark-text hover:text-accent leading-snug">${item.title}</p>
            ${item.meta ? `<p class="text-[10px] text-dark-text2 mt-0.5">${item.meta}</p>` : ''}
        </a>
    `).join('');
}

/**
 * Render the top-of-page 台股大盤 (TAIEX) + 台指期夜盤 hero section.
 * TAIEX itself is the actual index this whole dashboard exists to monitor,
 * so it gets the most prominent placement on the page. The night-session gap
 * sits right beside it since it's the overnight lead-in to TAIEX's next open
 * — but per the tooltip on the card, it's retrospective (posted ~16:30
 * Taipei), not a live intraday feed.
 */
function updateTaiexSection() {
    try {
        const summary = DataManager.getSummary() || {};
        const macro = summary.macro || {};
        const chip = summary.chip || {};

        const valueEl = document.getElementById('taiex-value');
        const changeEl = document.getElementById('taiex-change');
        if (valueEl && changeEl && macro.taiex && macro.taiex.value !== null && macro.taiex.value !== undefined) {
            const val = macro.taiex.value;
            const change = macro.taiex.change || 0;
            const changePct = macro.taiex.change_pct || 0;
            const colorClass = change >= 0 ? 'text-kd-red' : 'text-kd-green';
            const sign = change >= 0 ? '+' : '';
            valueEl.textContent = val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            changeEl.className = `text-lg font-semibold ${colorClass}`;
            changeEl.textContent = `${sign}${change.toFixed(2)} (${sign}${changePct.toFixed(2)}%)`;
        }

        const nightValueEl = document.getElementById('taiex-night-value');
        const nightGapEl = document.getElementById('taiex-night-gap');
        const nightDateEl = document.getElementById('taiex-night-date');
        if (nightValueEl && nightGapEl && chip.night_session && chip.night_session.gap_pct !== null && chip.night_session.gap_pct !== undefined) {
            const ns = chip.night_session;
            // Gap down = risk signal, so it gets kd-green (matches this
            // dashboard's "green = bearish/sell-side" convention elsewhere).
            const colorClass = ns.gap_pct >= 0 ? 'text-kd-red' : 'text-kd-green';
            const sign = ns.gap_pct >= 0 ? '+' : '';
            nightValueEl.textContent = ns.close ? ns.close.toLocaleString('en-US') : '-';
            nightGapEl.className = `text-base font-semibold ${colorClass}`;
            nightGapEl.textContent = `${sign}${ns.gap} (${sign}${ns.gap_pct.toFixed(2)}%)`;
            if (nightDateEl) nightDateEl.textContent = ns.date ? `(${ns.date})` : '';
        }
    } catch (e) {
        console.error("Error updating TAIEX section:", e);
    }
}

/**
 * Render the 訊號共振 (signal confluence) top/bottom turning-point panel.
 * Backed by src/signal_confluence.py — see that module's docstring for the
 * exact condition definitions and thresholds. Conditions marked 'partial'
 * only verify half of the original AND-condition (the TAIFEX futures/options
 * leg isn't fetched yet) and are visually flagged as such, never presented
 * the same as a fully-verified trigger.
 */
function renderSignalConfluence() {
    try {
        const summary = DataManager.getSummary() || {};
        const sc = summary.signal_confluence || { available: false };
        const dateEl = document.getElementById('confluence-date');
        const body = document.getElementById('confluence-body');
        if (!body) return;

        if (!sc.available) {
            if (dateEl) dateEl.textContent = '';
            const days = sc.history_days || 0;
            const minDays = sc.min_history_days || 21;
            body.innerHTML = `
                <div class="text-center py-4 text-dark-text2 text-sm">
                    <i class="fas fa-hourglass-half mr-1"></i>
                    歷史資料累積中（${days}/${minDays} 天），累積足夠天數後將自動開始評估
                </div>
            `;
            return;
        }

        if (dateEl) dateEl.textContent = `(資料日期: ${sc.as_of_date})`;

        const renderGroup = (group, title, colorClass, icon) => {
            if (!group) return '';
            const conditionsHtml = group.conditions.map(c => {
                let statusIcon, statusColor;
                if (c.status === true) { statusIcon = 'fa-circle-check'; statusColor = colorClass; }
                else if (c.status === false) { statusIcon = 'fa-circle-xmark'; statusColor = 'text-dark-text2 opacity-40'; }
                else { statusIcon = 'fa-circle-question'; statusColor = 'text-dark-text2 opacity-40'; }
                const partialBadge = c.completeness === 'partial'
                    ? '<span class="ml-1 px-1.5 py-0.5 rounded text-[9px] bg-yellow-500/20 text-yellow-400 align-middle">部分驗證</span>'
                    : '';
                return `
                    <div class="flex items-start gap-2 py-1.5 border-b border-dark-border/50 last:border-b-0">
                        <i class="fas ${statusIcon} ${statusColor} mt-0.5"></i>
                        <div class="flex-1 min-w-0">
                            <div class="text-xs text-dark-text font-medium">${c.label}${partialBadge}</div>
                            <div class="text-[10px] text-dark-text2 mt-0.5">${c.detail}</div>
                        </div>
                    </div>
                `;
            }).join('');

            return `
                <div class="flex-1 min-w-[280px]">
                    <div class="flex items-center justify-between mb-2">
                        <h3 class="text-sm font-bold ${colorClass}"><i class="fas ${icon} mr-1"></i>${title}</h3>
                        <span class="text-xs font-mono ${colorClass}">${group.triggered_count} / ${group.total_conditions} 項共振</span>
                    </div>
                    <div>${conditionsHtml}</div>
                </div>
            `;
        };

        body.innerHTML = `
            <div class="flex flex-col md:flex-row gap-4 mt-2">
                ${renderGroup(sc.top, '頂部結構與避險啟動', 'text-kd-red', 'fa-triangle-exclamation')}
                ${renderGroup(sc.bottom, '底部轉折與加碼訊號', 'text-kd-green', 'fa-arrow-trend-up')}
            </div>
        `;
    } catch (e) {
        console.error("Error rendering signal confluence:", e);
    }
}

/**
 * Render the 市場狀態 (Market Regime) badge inside the TAIEX hero card.
 * Backed by src/market_regime.py — see that module's docstring for the
 * exact classification logic (MA position/slope, VIX spike/rollover,
 * foreign flow reversal). Hidden entirely while regime detection doesn't
 * have enough history yet, rather than showing a misleading "資料不足" pill
 * every hour until then.
 */
const REGIME_STYLE = {
    BULL_TREND: { cls: 'bg-kd-red/15 text-kd-red', icon: 'fa-arrow-trend-up' },
    BULL_CORRECTION: { cls: 'bg-kd-yellow/15 text-kd-yellow', icon: 'fa-arrows-left-right' },
    BEAR_TREND: { cls: 'bg-kd-green/15 text-kd-green', icon: 'fa-arrow-trend-down' },
    PANIC: { cls: 'bg-kd-red/25 text-kd-red', icon: 'fa-triangle-exclamation' },
    RECOVERY: { cls: 'bg-kd-yellow/20 text-kd-yellow', icon: 'fa-life-ring' },
};
function renderRegimeBadge() {
    try {
        const summary = DataManager.getSummary() || {};
        const mr = summary.market_regime || { available: false };
        const badge = document.getElementById('regime-badge');
        const textEl = document.getElementById('regime-badge-text');
        if (!badge || !textEl) return;

        if (!mr.available || !REGIME_STYLE[mr.regime]) {
            badge.classList.add('hidden');
            return;
        }
        const style = REGIME_STYLE[mr.regime];
        badge.className = `inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold cursor-pointer info-trigger ${style.cls}`;
        badge.dataset.info = 'market_regime';
        textEl.textContent = `${mr.regime_label}（${mr.ma_period_used}日均線）`;
        badge.querySelector('i').className = `fas ${style.icon}`;
    } catch (e) {
        console.error("Error rendering regime badge:", e);
    }
}

/**
 * Render the 訊號評分 (Signal Score) 0-100 panel — Top Risk Score / Bottom
 * Setup Score, each broken into 5 weighted dimensions. Backed by
 * src/signal_score.py. See that module's docstring for why this is
 * presented as "how many known conditions are met" rather than a
 * probability — the caveat text is repeated here in the UI, not just in
 * the card's footer disclaimer, so it's visible right next to the number.
 */
function renderSignalScore() {
    try {
        const summary = DataManager.getSummary() || {};
        const ss = summary.signal_score || { available: false };
        const dateEl = document.getElementById('signal-score-date');
        const body = document.getElementById('signal-score-body');
        if (!body) return;

        if (!ss.available) {
            if (dateEl) dateEl.textContent = '';
            const days = ss.history_days || 0;
            const minDays = ss.min_history_days || 21;
            body.innerHTML = `
                <div class="text-center py-4 text-dark-text2 text-sm">
                    <i class="fas fa-hourglass-half mr-1"></i>
                    歷史資料累積中（${days}/${minDays} 天），累積足夠天數後將自動開始評分
                </div>
            `;
            return;
        }

        if (dateEl) dateEl.textContent = `(資料日期: ${ss.as_of_date})`;

        const dimLabels = {
            macro: '總經 Macro', chip_flow: '籌碼 Chip Flow', derivative: '衍生性商品 Derivative',
            technical: '技術面 Technical', sentiment: '情緒面 Sentiment'
        };

        const renderScoreCard = (group, title, colorClass, barClass, icon) => {
            if (!group) return '';
            const dimsHtml = group.dimensions.map(d => {
                const pct = d.cap > 0 ? Math.round((d.score / d.cap) * 100) : 0;
                const notesHtml = d.notes.length
                    ? `<div class="mt-1 space-y-0.5">${d.notes.map(n => `<div class="text-[10px] text-dark-text2 leading-snug">・${n}</div>`).join('')}</div>`
                    : '';
                return `
                    <div class="py-1.5">
                        <div class="flex items-center justify-between text-[11px] mb-1">
                            <span class="text-dark-text">${dimLabels[d.name] || d.name}</span>
                            <span class="font-mono ${colorClass}">${d.score} / ${d.cap}</span>
                        </div>
                        <div class="h-1.5 rounded-full bg-dark-bg overflow-hidden">
                            <div class="h-full ${barClass} rounded-full" style="width: ${pct}%"></div>
                        </div>
                        ${notesHtml}
                    </div>
                `;
            }).join('');

            return `
                <div class="flex-1 min-w-[280px]">
                    <div class="flex items-center justify-between mb-1">
                        <h3 class="text-sm font-bold ${colorClass}"><i class="fas ${icon} mr-1"></i>${title}</h3>
                        <span class="text-2xl font-bold font-mono ${colorClass}">${group.total}<span class="text-xs text-dark-text2">/100</span></span>
                    </div>
                    <div class="divide-y divide-dark-border/50">${dimsHtml}</div>
                </div>
            `;
        };

        body.innerHTML = `
            <div class="flex flex-col md:flex-row gap-4 mt-2">
                ${renderScoreCard(ss.top, '頂部風險分數', 'text-kd-red', 'bg-kd-red', 'fa-triangle-exclamation')}
                ${renderScoreCard(ss.bottom, '底部佈局分數', 'text-kd-green', 'bg-kd-green', 'fa-arrow-trend-up')}
            </div>
        `;
    } catch (e) {
        console.error("Error rendering signal score:", e);
    }
}

/**
 * Render the 台積電 (2330) Investment Score panel. Backed by
 * src/tsmc_analyzer.py — see that module's docstring for the full 10-
 * dimension model and why 2330 gets a dedicated fundamentals-aware score
 * instead of being treated like any other KD-only ticker.
 */
const TSMC_DIM_LABELS = {
    revenue_momentum: '營收動能', margin_eps_trend: '毛利率/EPS趨勢', guidance: '法說會財測指引',
    technical_trend: '技術趨勢', momentum_composite: '動能綜合(KD/RSI/MACD)', relative_strength: '相對強弱',
    institutional: '外資籌碼', adr_premium: 'ADR溢折價', market_regime: '大盤環境', valuation: '估值(本益比百分位)'
};
const TSMC_RECOMMENDATION_STYLE = {
    '強勢加碼區': 'bg-kd-red/20 text-kd-red', '偏多持有': 'bg-kd-red/10 text-kd-red',
    '中性持有': 'bg-kd-yellow/15 text-kd-yellow', '減碼/等待': 'bg-kd-green/10 text-kd-green',
    '防守': 'bg-kd-green/20 text-kd-green'
};
function renderTsmcAnalysis() {
    try {
        const summary = DataManager.getSummary() || {};
        const t = summary.tsmc_analysis || { available: false };
        const dateEl = document.getElementById('tsmc-date');
        const body = document.getElementById('tsmc-body');
        if (!body) return;

        if (!t.available) {
            if (dateEl) dateEl.textContent = '';
            body.innerHTML = `
                <div class="text-center py-4 text-dark-text2 text-sm">
                    <i class="fas fa-hourglass-half mr-1"></i>
                    資料尚不足以計算台積電投資決策分數（${t.reason || '請稍候，資料會隨每日執行自動累積'}）
                </div>
            `;
            return;
        }
        if (dateEl) dateEl.textContent = `(涵蓋 ${t.coverage} 項構面)`;

        const recStyle = TSMC_RECOMMENDATION_STYLE[t.recommendation] || 'bg-dark-bg text-dark-text2';
        const buyPointsHtml = (t.buy_points && t.buy_points.length)
            ? t.buy_points.map(bp => `
                <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-accent/15 text-accent mr-2 mb-1" title="${bp.detail}">
                    <i class="fas fa-crosshairs"></i> ${bp.label}
                </span>
            `).join('')
            : '<span class="text-xs text-dark-text2">目前未觸發任一設定買點</span>';

        const dimsHtml = t.dimensions.map(d => {
            if (!d.available) {
                return `
                    <div class="py-1.5 opacity-50">
                        <div class="flex items-center justify-between text-[11px] mb-1">
                            <span class="text-dark-text">${TSMC_DIM_LABELS[d.name] || d.name}</span>
                            <span class="font-mono text-dark-text2">資料不足</span>
                        </div>
                        <div class="text-[10px] text-dark-text2">${(d.notes || []).join('；')}</div>
                    </div>
                `;
            }
            const pct = d.cap > 0 ? Math.round((d.score / d.cap) * 100) : 0;
            const barClass = pct >= 60 ? 'bg-kd-red' : pct >= 30 ? 'bg-kd-yellow' : 'bg-kd-green';
            const notesHtml = (d.notes || []).length
                ? `<div class="mt-1 space-y-0.5">${d.notes.map(n => `<div class="text-[10px] text-dark-text2 leading-snug">・${n}</div>`).join('')}</div>`
                : '';
            return `
                <div class="py-1.5">
                    <div class="flex items-center justify-between text-[11px] mb-1">
                        <span class="text-dark-text">${TSMC_DIM_LABELS[d.name] || d.name}</span>
                        <span class="font-mono text-dark-text">${d.score} / ${d.cap}</span>
                    </div>
                    <div class="h-1.5 rounded-full bg-dark-bg overflow-hidden">
                        <div class="h-full ${barClass} rounded-full" style="width: ${pct}%"></div>
                    </div>
                    ${notesHtml}
                </div>
            `;
        }).join('');

        body.innerHTML = `
            <div class="flex items-center justify-between flex-wrap gap-3 mt-2 mb-3">
                <div class="flex items-baseline gap-3">
                    <span class="text-3xl font-bold font-mono text-white">${t.total}<span class="text-sm text-dark-text2">/100</span></span>
                    <span class="px-3 py-1 rounded-full text-sm font-semibold ${recStyle}">${t.recommendation}</span>
                </div>
                <div>${buyPointsHtml}</div>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 divide-y divide-dark-border/50 md:divide-y-0">
                ${dimsHtml}
            </div>
        `;
    } catch (e) {
        console.error("Error rendering TSMC analysis:", e);
    }
}

/**
 * Update last updated timestamp
 */
function updateLastUpdated() {
    const stockData = DataManager.stockData;
    if (stockData && stockData.last_updated) {
        const formatted = DataManager.formatDate(stockData.last_updated);
        document.getElementById('last-updated').innerHTML =
            `<i class="fas fa-sync-alt mr-1"></i> 更新時間: ${formatted}`;
    }
}

/**
 * Filter stocks by category
 */
function filterStocks(category) {
    currentFilter = category;

    // Update tab styles
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active', 'border-accent', 'text-accent');
        btn.classList.add('border-transparent', 'text-dark-text2');
    });
    document.getElementById(`tab-${category}`).classList.add('active', 'border-accent', 'text-accent');
    document.getElementById(`tab-${category}`).classList.remove('border-transparent', 'text-dark-text2');

    renderStockGrid();
}

/**
 * Get filtered stocks based on current filter
 */
let currentScoreFilter = 'all';

function getFilteredStocks() {
    let stocks;
    switch (currentFilter) {
        case 'tw':
            stocks = DataManager.getStocksByMarket('TW');
            break;
        case 'us':
            stocks = DataManager.getStocksByMarket('US');
            break;
        case 'alerts':
            stocks = DataManager.getAlertStocks();
            break;
        default:
            stocks = DataManager.getAllStocks();
    }
    // Apply score filter
    if (currentScoreFilter !== 'all') {
        stocks = stocks.filter(s => {
            const score = (s.score || {}).total || 50;
            switch (currentScoreFilter) {
                case 'strong_buy': return score >= 90;
                case 'buy': return score >= 70 && score < 90;
                case 'hold': return score >= 50 && score < 70;
                case 'reduce': return score >= 30 && score < 50;
                case 'sell': return score < 30;
                default: return true;
            }
        });
    }
    return stocks;
}

/**
 * Render stock grid
 */
function renderStockGrid() {
    const grid = document.getElementById('stock-grid');
    const stocks = getFilteredStocks();

    if (stocks.length === 0) {
        grid.innerHTML = `
            <div class="col-span-full text-center py-8 text-dark-text2">
                <i class="fas fa-inbox text-4xl mb-2 opacity-50"></i>
                <p>沒有符合條件的股票</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = stocks.map(stock => createStockCard(stock)).join('');
}

/**
 * KD State (see src/kd_calculator.py's analyze_kd_signal docstring) — a
 * finer-grained read on today's K/D than the raw overbought/oversold zone
 * alone, distinguishing e.g. "overbought but momentum still building" from
 * "overbought and stalling" by also looking at yesterday's K/D (crossover +
 * whether the K-D gap is widening or narrowing).
 */
const KD_STATE_STYLE = {
    GOLDEN_CROSS: { label: '黃金交叉', cls: 'bg-kd-red/15 text-kd-red' },
    DEATH_CROSS: { label: '死亡交叉', cls: 'bg-kd-green/15 text-kd-green' },
    OVERBOUGHT_BUT_RISING: { label: '超買中·動能未歇', cls: 'bg-kd-red/15 text-kd-red' },
    OVERBOUGHT_REVERSAL: { label: '超買轉弱', cls: 'bg-kd-yellow/15 text-kd-yellow' },
    OVERBOUGHT: { label: '超買', cls: 'bg-kd-yellow/15 text-kd-yellow' },
    OVERSOLD_REVERSAL: { label: '超賣反轉', cls: 'bg-kd-green/15 text-kd-green' },
    OVERSOLD_BUT_RISING: { label: '超賣回升中', cls: 'bg-kd-yellow/15 text-kd-yellow' },
    OVERSOLD: { label: '超賣', cls: 'bg-kd-yellow/15 text-kd-yellow' },
    BULLISH_MOMENTUM: { label: '多頭動能', cls: 'bg-kd-red/10 text-kd-red' },
    BEARISH_MOMENTUM: { label: '空頭動能', cls: 'bg-kd-green/10 text-kd-green' },
    NEUTRAL: { label: '中性', cls: 'bg-dark-bg text-dark-text2' },
};
function renderKdStateBadge(kdState) {
    const style = KD_STATE_STYLE[kdState];
    if (!style) return '';
    return `
        <div class="mt-1.5 text-right">
            <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium cursor-pointer info-trigger ${style.cls}" data-info="kd_state">
                ${style.label}
            </span>
        </div>
    `;
}

/**
 * Create stock card HTML - Dark Theme
 */
function createStockCard(stock) {
    const status = DataManager.getKDStatus(stock.kd_k, stock.kd_d);
    const statusClass = status === 'overbought' ? 'overbought pulse-alert-overbought' :
                        status === 'oversold' ? 'oversold pulse-alert-oversold' : 'normal';
    const statusBadgeClass = status === 'overbought' ? 'overbought' :
                             status === 'oversold' ? 'oversold' : 'normal';
    const statusText = status === 'overbought' ? '超買' :
                       status === 'oversold' ? '超賣' : '正常';

    const textColorClass = status === 'overbought' ? 'text-kd-red' :
                          status === 'oversold' ? 'text-kd-green' : 'text-white';
    const priceColorClass = status === 'overbought' ? 'text-kd-red' :
                           status === 'oversold' ? 'text-kd-green' : 'text-white';
    const kdColorClass = status === 'overbought' ? 'text-kd-red' :
                        status === 'oversold' ? 'text-kd-green' : 'text-dark-text';

    const kdKClass = stock.kd_k >= 80 ? 'high' : stock.kd_k <= 20 ? 'low' : 'normal';
    const kdDClass = stock.kd_d >= 80 ? 'high' : stock.kd_d <= 20 ? 'low' : 'normal';

    const progressValue = stock.kd_k || 50;
    const progressClass = progressValue >= 80 ? 'high' : progressValue <= 20 ? 'low' : 'normal';

    const currency = stock.market === 'TW' ? 'TWD' : 'USD';
    const marketClass = stock.market === 'TW' ? 'tw' : 'us';

    // Score badge
    const score = stock.score || { total: 50, recommendation: '觀望' };
    const scoreTotal = score.total || 50;
    let scoreColorClass = 'bg-gray-600';
    let scoreTextClass = 'text-white';
    let scoreLabel = score.recommendation || '觀望';
    if (scoreTotal >= 90) { scoreColorClass = 'bg-emerald-600'; scoreTextClass = 'text-white'; }
    else if (scoreTotal >= 70) { scoreColorClass = 'bg-emerald-500/80'; scoreTextClass = 'text-white'; }
    else if (scoreTotal >= 50) { scoreColorClass = 'bg-yellow-500/80'; scoreTextClass = 'text-black'; }
    else if (scoreTotal >= 30) { scoreColorClass = 'bg-orange-500/80'; scoreTextClass = 'text-white'; }
    else { scoreColorClass = 'bg-red-500/80'; scoreTextClass = 'text-white'; }

    const changePct = stock.change_pct || 0;
    const changeClass = changePct >= 0 ? 'text-kd-red' : 'text-kd-green';
    const changeIcon = changePct >= 0 ? '▲' : '▼';
    const changeText = `${changeIcon} ${Math.abs(changePct).toFixed(2)}%`;

    // Extended Hours Data
    let extendedHoursHtml = '';
    const extra = stock.extra_data || {};
    if (stock.market === 'US') {
        if (extra.pre_market_price) {
            const preChange = ((extra.pre_market_price - stock.current_price) / stock.current_price * 100).toFixed(2);
            const preClass = preChange >= 0 ? 'text-kd-red' : 'text-kd-green';
            extendedHoursHtml += `<p class="text-[10px] ${preClass}">盤前: $${extra.pre_market_price.toFixed(2)} (${preChange}%)</p>`;
        }
        if (extra.post_market_price) {
            const postChange = ((extra.post_market_price - stock.current_price) / stock.current_price * 100).toFixed(2);
            const postClass = postChange >= 0 ? 'text-kd-red' : 'text-kd-green';
            extendedHoursHtml += `<p class="text-[10px] ${postClass}">盤後: $${extra.post_market_price.toFixed(2)} (${postChange}%)</p>`;
        }
    }

    return `
        <div class="stock-card ${statusClass}" onclick="selectStockForChart('${stock.symbol}')">
            <div class="flex justify-between items-start mb-2">
                <div>
                    <h3 class="font-bold text-lg ${textColorClass}">${stock.symbol}</h3>
                    <p class="text-sm ${status === 'overbought' ? 'text-kd-red' : status === 'oversold' ? 'text-kd-green' : 'text-dark-text2'}">${stock.name}</p>
                </div>
                <div class="text-right">
                    <span class="market-badge ${marketClass}">${stock.market}</span>
                    <span class="status-badge ${statusBadgeClass} ml-1">${statusText}</span>
                    <div class="mt-1 inline-flex items-center px-2 py-0.5 rounded text-xs font-bold ${scoreColorClass} ${scoreTextClass}" title="${scoreLabel}">
                        ${scoreTotal}分
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-2 gap-4 mb-3">
                <div>
                    <p class="text-xs text-dark-text2">現價</p>
                    <div class="flex items-baseline space-x-1">
                        <p class="font-bold ${priceColorClass}">${DataManager.formatPrice(stock.current_price, currency)}</p>
                        <span class="text-[10px] font-bold ${changeClass}">${changeText}</span>
                    </div>
                    ${extendedHoursHtml}
                </div>
                <div class="text-right">
                    <p class="text-xs text-dark-text2">更新時間</p>
                    <p class="text-xs text-dark-text2">${stock.last_updated ? DataManager.formatDate(stock.last_updated).split(' ')[0] : '-'}</p>
                </div>
            </div>

            ${createVolumeSparkline(stock.history, stock.market)}

            <div class="border-t border-dark-border pt-3">
                <div class="flex justify-between items-center mb-2">
                    <span class="text-sm text-dark-text2">KD-K</span>
                    <span class="kd-value ${kdKClass} ${kdColorClass}">${stock.kd_k !== null ? stock.kd_k.toFixed(2) : '-'}</span>
                </div>
                <div class="flex justify-between items-center mb-2">
                    <span class="text-sm text-dark-text2">KD-D</span>
                    <span class="kd-value ${kdDClass} ${kdColorClass}">${stock.kd_d !== null ? stock.kd_d.toFixed(2) : '-'}</span>
                </div>
                <div class="kd-progress-bar">
                    <div class="kd-progress-fill ${progressClass}" style="width: ${Math.min(Math.max(progressValue, 0), 100)}%"></div>
                </div>
                ${renderKdStateBadge(stock.kd_state)}
            </div>

            <div class="border-t border-dark-border pt-3 mt-2">
                <div class="flex justify-between items-center mb-1">
                    <span class="text-xs text-dark-text2">乖離率(5日)</span>
                    <span class="text-xs font-bold ${getBiasColorClass(stock.bias_5)}">${stock.bias_5 !== null ? stock.bias_5.toFixed(2) : '-'}%</span>
                </div>
                <div class="flex justify-between items-center mb-1">
                    <span class="text-xs text-dark-text2">乖離率(10日)</span>
                    <span class="text-xs font-bold ${getBiasColorClass(stock.bias_10)}">${stock.bias_10 !== null ? stock.bias_10.toFixed(2) : '-'}%</span>
                </div>
                <div class="flex justify-between items-center mb-1">
                    <span class="text-xs text-dark-text2">乖離率(20日)</span>
                    <span class="text-xs font-bold ${getBiasColorClass(stock.bias_20)}">${stock.bias_20 !== null ? stock.bias_20.toFixed(2) : '-'}%</span>
                </div>
            </div>

            ${createInstitutionalFlowSection(stock)}
            ${createPatternSection(stock.patterns)}
            <div class="mt-3 pt-2 border-t border-dark-border flex justify-between items-center">
                <span class="text-[10px] text-dark-text2 opacity-60">點擊卡片查看K線</span>
                <button onclick="event.stopPropagation(); showScoreModal('${stock.symbol}')" class="text-xs px-2 py-1 rounded border border-accent/30 text-accent hover:bg-accent/10 transition">
                    <i class="fas fa-chart-pie mr-1"></i>評分明細
                </button>
            </div>
        </div>
    `;
}

/**
 * Create volume sparkline chart
 */
function createVolumeSparkline(history, market) {
    if (!history || history.length < 5) {
        return '';
    }

    const recentData = history.slice(-10);
    const volumes = recentData.map(d => d.volume || 0);

    if (volumes.length === 0 || volumes.every(v => v === 0)) {
        return '';
    }

    const maxVolume = Math.max(...volumes);
    const minVolume = Math.min(...volumes);
    const range = maxVolume - minVolume || 1;

    const avgVolume = volumes.reduce((a, b) => a + b, 0) / volumes.length;
    const latestVolume = volumes[volumes.length - 1];

    let trendColor = 'text-gray-500';
    let trendIcon = '→';
    if (latestVolume > avgVolume * 1.3) {
        trendColor = 'text-kd-red';
        trendIcon = '↑';
    } else if (latestVolume < avgVolume * 0.7) {
        trendColor = 'text-kd-green';
        trendIcon = '↓';
    }

    const width = 100;
    const height = 30;
    const barWidth = width / volumes.length - 1;

    let barsHtml = '';
    volumes.forEach((vol, i) => {
        const height_pct = ((vol - minVolume) / range) * 80 + 20;
        const x = i * (barWidth + 1);
        const y = height - (height_pct / 100 * height);

        let barColor = '#555555';
        const volRatio = vol / avgVolume;
        if (volRatio > 1.5) barColor = '#ff3333';
        else if (volRatio > 1.2) barColor = '#ffaa00';
        else if (volRatio < 0.6) barColor = '#00cc66';

        barsHtml += `<rect x="${x}" y="${y}" width="${barWidth}" height="${height_pct / 100 * height}" fill="${barColor}" rx="1" />`;
    });

    const formatVolume = (vol) => {
        if (vol >= 1000000) return (vol / 1000000).toFixed(1) + 'M';
        if (vol >= 1000) return (vol / 1000).toFixed(1) + 'K';
        return vol.toString();
    };

    return `
        <div class="mb-3">
            <div class="flex justify-between items-center mb-1">
                <span class="text-xs text-dark-text2">成交量趨勢</span>
                <span class="text-xs ${trendColor} font-medium">${trendIcon} ${formatVolume(latestVolume)}</span>
            </div>
            <svg width="100%" height="${height}" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" class="volume-sparkline">
                ${barsHtml}
            </svg>
            <div class="flex justify-between text-xs text-dark-text2 mt-1 opacity-50">
                <span>10日前</span>
                <span>今日</span>
            </div>
        </div>
    `;
}

/**
 * Create per-stock 外資/投信買賣超 section (TW stocks only). Shows the latest
 * day's foreign net buy/sell (張, i.e. thousands of shares) plus the 3-day
 * cumulative figure that alert_checker.py's filters actually key off of, so
 * the number on screen matches the reasoning behind any 高信心/疑似鈍化
 * badge shown on a related alert.
 */
function createInstitutionalFlowSection(stock) {
    if (stock.market !== 'TW') return '';
    const inst = stock.institutional;
    if (!inst || inst.foreign_net === null || inst.foreign_net === undefined) return '';

    const lots = (shares) => (shares / 1000).toFixed(0);
    const dayVal = inst.foreign_net;
    const dayClass = dayVal >= 0 ? 'text-kd-red' : 'text-kd-green';
    const daySign = dayVal >= 0 ? '+' : '';

    let cumHtml = '';
    if (inst.foreign_net_3d !== null && inst.foreign_net_3d !== undefined) {
        const cumVal = inst.foreign_net_3d;
        const cumClass = cumVal >= 0 ? 'text-kd-red' : 'text-kd-green';
        const cumSign = cumVal >= 0 ? '+' : '';
        cumHtml = `<span class="text-[10px] text-dark-text2 ml-1">(近3日 ${cumSign}${lots(cumVal)}張)</span>`;
    }

    return `
        <div class="border-t border-dark-border pt-2 mt-2">
            <div class="flex justify-between items-center">
                <span class="text-xs text-dark-text2">個股外資買賣超${inst.date ? ` (${inst.date})` : ''}</span>
                <span class="text-xs font-bold ${dayClass}">${daySign}${lots(dayVal)}張${cumHtml}</span>
            </div>
        </div>
    `;
}

/**
 * Create pattern analysis section HTML
 */
function createPatternSection(patterns) {
    if (!patterns || !patterns.patterns || patterns.patterns.length === 0) {
        return '';
    }

    const signalEmojis = {
        'BUY': '🟢',
        'SELL': '🔴',
        'HOLD': '🟡',
        'AVOID': '⚫'
    };

    const signalLabels = {
        'BUY': '買入',
        'SELL': '賣出',
        'HOLD': '持有',
        'AVOID': '避開'
    };

    const dominantSignal = patterns.dominant_signal || 'HOLD';
    const topPatterns = patterns.patterns.slice(0, 2);

    let patternsHtml = topPatterns.map(p => {
        const emoji = signalEmojis[p.signal] || '⚪';
        return `
            <div class="flex items-center justify-between text-xs mb-1">
                <span class="text-dark-text2">${emoji} ${p.pattern_id}-${p.pattern_name}</span>
                <span class="font-medium text-dark-text">${p.confidence}%</span>
            </div>
        `;
    }).join('');

    return `
        <div class="border-t border-dark-border mt-2 pt-2">
            <div class="flex items-center justify-between mb-1">
                <span class="text-xs text-dark-text2">交易信號</span>
                <span class="text-xs font-bold ${getSignalColorClass(dominantSignal)}">
                    ${signalEmojis[dominantSignal]} ${signalLabels[dominantSignal]}
                </span>
            </div>
            ${patternsHtml}
        </div>
    `;
}

/**
 * Get CSS color class for signal
 */
function getSignalColorClass(signal) {
    const classes = {
        'BUY': 'text-kd-green',
        'SELL': 'text-kd-red',
        'HOLD': 'text-kd-yellow',
        'AVOID': 'text-dark-text2'
    };
    return classes[signal] || 'text-dark-text2';
}

/**
 * Get CSS color class for BIAS value
 * Taiwan convention: positive (above MA) = red, negative (below MA) = green
 */
function getBiasColorClass(bias) {
    if (bias === null || bias === undefined) return 'text-dark-text2';
    if (bias > 5) return 'text-kd-red';
    if (bias > 0) return 'text-kd-red/70';
    if (bias < -5) return 'text-kd-green';
    if (bias < 0) return 'text-kd-green/70';
    return 'text-dark-text2';
}

/**
 * Render alert history
 */
function renderAlertHistory() {
    const container = document.getElementById('alert-history');
    const alerts = DataManager.getAlerts();

    if (alerts.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4 text-dark-text2">
                <i class="fas fa-check-circle text-kd-green text-2xl mb-2"></i>
                <p>暫無警示記錄</p>
            </div>
        `;
        return;
    }

    container.innerHTML = alerts.map(alert => createAlertItem(alert)).join('');
}

/**
 * Render the filter-confidence badge for an alert: "high" means the
 * MA/Bollinger/MACD filters (see alert_checker.py._evaluate_filters) agree
 * with the raw KD extreme reading; "low" flags a likely 鈍化 (indicator
 * stuck at an extreme through a real trend, not a reversal) so the raw KD
 * signal alone shouldn't be acted on; "unknown" means there wasn't enough
 * price history yet to run the filters.
 */
function renderFilterBadge(confidence) {
    if (confidence === 'high') {
        return '<span class="ml-2 px-2 py-0.5 rounded text-xs bg-blue-900/30 text-blue-400"><i class="fas fa-check-circle"></i> 高信心</span>';
    }
    if (confidence === 'low') {
        return '<span class="ml-2 px-2 py-0.5 rounded text-xs bg-yellow-900/30 text-yellow-400"><i class="fas fa-triangle-exclamation"></i> 疑似鈍化</span>';
    }
    return '<span class="ml-2 px-2 py-0.5 rounded text-xs bg-gray-700/40 text-dark-text2">資料不足</span>';
}

/**
 * Create alert item HTML
 */
function createAlertItem(alert) {
    const typeClass = alert.type === 'overbought' ? 'overbought' : 'oversold';
    const icon = alert.type === 'overbought' ? 'fa-arrow-up text-kd-red' : 'fa-arrow-down text-kd-green';
    const title = alert.type === 'overbought' ? '超買警告' : '超賣提醒';

    const passed = Array.isArray(alert.filter_passed) ? alert.filter_passed : [];
    const cautions = Array.isArray(alert.filter_cautions) ? alert.filter_cautions : [];
    const hasFilterInfo = passed.length > 0 || cautions.length > 0;

    const filterNotesHtml = hasFilterInfo ? `
        <div class="mt-2 pt-2 border-t border-dark-border/60 text-xs space-y-1">
            ${passed.map(p => `<div class="text-dark-text2"><i class="fas fa-check text-kd-red opacity-70 mr-1"></i>${p}</div>`).join('')}
            ${cautions.map(c => `<div class="text-yellow-400/90"><i class="fas fa-triangle-exclamation opacity-70 mr-1"></i>${c}</div>`).join('')}
        </div>
    ` : '';

    return `
        <div class="alert-item ${typeClass} ${alert.acknowledged ? 'acknowledged' : ''}">
            <div class="flex-shrink-0 mr-3">
                <i class="fas ${icon} text-xl"></i>
            </div>
            <div class="flex-grow">
                <div class="flex justify-between items-start flex-wrap gap-y-1">
                    <div>
                        <span class="font-semibold text-white">${alert.symbol}</span>
                        <span class="text-sm text-dark-text2 ml-1">${alert.name}</span>
                        <span class="ml-2 px-2 py-0.5 rounded text-xs ${alert.type === 'overbought' ? 'bg-red-900/30 text-kd-red' : 'bg-green-900/30 text-kd-green'}">
                            ${title}
                        </span>
                        ${alert.filter_confidence ? renderFilterBadge(alert.filter_confidence) : ''}
                        ${alert.market_regime_label ? `<span class="ml-2 px-2 py-0.5 rounded text-xs bg-dark-bg border border-dark-border text-dark-text2"><i class="fas fa-compass opacity-70"></i> ${alert.market_regime_label}</span>` : ''}
                    </div>
                    <span class="text-xs text-dark-text2">${DataManager.formatDate(alert.timestamp)}</span>
                </div>
                <div class="mt-1 text-sm text-dark-text2">
                    KD-K: <span class="font-semibold text-white">${alert.kd_k}</span> |
                    KD-D: <span class="font-semibold text-white">${alert.kd_d}</span> |
                    價格: <span class="font-semibold text-white">${DataManager.formatPrice(alert.current_price, alert.market === 'TW' ? 'TWD' : 'USD')}</span>
                </div>
                ${filterNotesHtml}
            </div>
        </div>
    `;
}

/**
 * Populate chart stock selector
 */
function populateChartSelect() {
    const select = document.getElementById('chart-stock-select');
    const stocks = DataManager.getAllStocks();

    select.innerHTML = '<option value="">-- 選擇股票 --</option>' +
        stocks.map(stock => `<option value="${stock.symbol}">${stock.symbol} - ${stock.name}</option>`).join('');

    select.addEventListener('change', (e) => {
        if (e.target.value) {
            updateChart(e.target.value);
        }
    });
}

/**
 * Select stock for chart (when clicking on a card)
 */
async function selectStockForChart(symbol) {
    const select = document.getElementById('chart-stock-select');
    select.value = symbol;
    await updateChart(symbol);

    // Scroll to chart
    document.getElementById('chart-section').scrollIntoView({ behavior: 'smooth', block: 'center' });
}

/**
 * Update chart with stock data - ECharts
 */
async function updateChart(symbol) {
    const stock = DataManager.getStock(symbol);
    if (!stock) return;

    // Try to load real history from CSV first
    let history = await DataManager.loadStockHistory(symbol);

    if (!history || history.length === 0) {
        // Fallback to sample data if no real history available
        history = generateSampleHistory(stock);
    }

    StockChart.update(symbol, stock.name, history);
}

/**
 * Generate sample history for demo when no real data
 */
function generateSampleHistory(stock) {
    const days = 60;
    const history = [];
    const basePrice = stock?.current_price || 100;

    for (let i = days; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);

        const randomChange = (Math.random() - 0.5) * basePrice * 0.03;
        const price = basePrice + randomChange + (Math.sin(i / 5) * basePrice * 0.05);
        const open = price * (1 + (Math.random() - 0.5) * 0.01);
        const high = Math.max(open, price) * (1 + Math.random() * 0.01);
        const low = Math.min(open, price) * (1 - Math.random() * 0.01);

        const k = 50 + Math.sin(i / 3) * 40 + (Math.random() - 0.5) * 10;
        const d = k + (Math.random() - 0.5) * 5;

        history.push({
            date: date.toISOString(),
            open: open,
            high: high,
            low: low,
            close: price,
            volume: Math.floor(Math.random() * 10000000) + 1000000,
            kd_k: Math.max(0, Math.min(100, k)),
            kd_d: Math.max(0, Math.min(100, d))
        });
    }

    return history;
}

/**
 * Refresh data (can be called periodically)
 */
async function refreshData() {
    console.log('Refreshing data...');
    await DataManager.loadData();
    updateStats();
    updateTaiexSection();
    renderRegimeBadge();
    renderMarketNews();
    updateChipStats();
    renderSignalScore();
    renderSignalConfluence();
    renderTsmcAnalysis();
    renderStockGrid();
    renderAlertHistory();
    updateLastUpdated();

    // Refresh chart if a stock is selected
    const select = document.getElementById('chart-stock-select');
    if (select.value) {
        await updateChart(select.value);
    }
}

// Auto-refresh every 5 minutes (if page is active)
setInterval(() => {
    if (!document.hidden) {
        refreshData();
    }
}, 5 * 60 * 1000);

// ── Score Filter ──────────────────────────────────────────
function filterByScore(scoreFilter) {
    currentScoreFilter = scoreFilter;
    document.querySelectorAll('.score-btn').forEach(btn => {
        btn.classList.remove('active', 'bg-accent/20', 'text-accent', 'border-accent/30');
        btn.classList.add('bg-dark-bg', 'text-dark-text2', 'border-dark-border');
    });
    const activeBtn = document.getElementById('score-' + scoreFilter);
    if (activeBtn) {
        activeBtn.classList.remove('bg-dark-bg', 'text-dark-text2', 'border-dark-border');
        activeBtn.classList.add('active', 'bg-accent/20', 'text-accent', 'border-accent/30');
    }
    renderStockGrid();
}

// ── Score Modal ──────────────────────────────────────────
function showScoreModal(symbol) {
    const stock = DataManager.getStock(symbol);
    if (!stock || !stock.score) return;
    const score = stock.score;
    const details = score.details || {};
    const raw = score.raw || {};

    document.getElementById('modal-title').textContent = stock.symbol;
    document.getElementById('modal-subtitle').textContent = stock.name + ' - ' + DataManager.formatPrice(stock.current_price, stock.market === 'TW' ? 'TWD' : 'USD');

    const recEl = document.getElementById('modal-recommendation');
    recEl.textContent = score.recommendation + ' (' + score.total + '分)';
    let recColor = 'text-yellow-400';
    if (score.total >= 70) recColor = 'text-emerald-400';
    else if (score.total < 30) recColor = 'text-red-400';
    else if (score.total < 50) recColor = 'text-orange-400';
    recEl.className = 'text-lg font-bold mt-2 ' + recColor;

    renderScoreBars(details);
    renderScoreGauge(score.total);
    renderScoreRadar(details);
    renderRawMetrics(raw);
    renderScoreSummary(score);

    document.getElementById('score-modal').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeScoreModal() {
    document.getElementById('score-modal').classList.add('hidden');
    document.body.style.overflow = '';
}

function renderScoreBars(details) {
    const dims = [
        { key: 'kd', label: 'KD 動能', weight: 20 },
        { key: 'rsi', label: 'RSI 強弱', weight: 15 },
        { key: 'ma_bias', label: '均線乖離', weight: 15 },
        { key: 'macd', label: 'MACD 趨勢', weight: 15 },
        { key: 'volume_price', label: '量價結構', weight: 15 },
        { key: 'trend', label: '趨勢動能', weight: 20 },
    ];
    let html = '';
    dims.forEach(d => {
        const s = (details[d.key] || {}).score || 50;
        let barColor = '#eab308';
        if (s >= 70) barColor = '#10b981';
        else if (s < 30) barColor = '#ef4444';
        else if (s < 50) barColor = '#f97316';
        html += `
            <div class="flex items-center gap-2">
                <span class="text-xs text-dark-text2 w-20 text-right">${d.label}</span>
                <div class="flex-1 h-2 bg-dark-bg rounded-full overflow-hidden border border-dark-border">
                    <div class="h-full rounded-full transition-all duration-500" style="width:${s}%; background:${barColor}"></div>
                </div>
                <span class="text-xs font-mono w-8 text-right" style="color:${barColor}">${s}</span>
            </div>
        `;
    });
    document.getElementById('score-bars').innerHTML = html;
}

function renderScoreGauge(total) {
    const el = document.getElementById('gauge-chart');
    let chart = echarts.getInstanceByDom(el);
    if (chart) chart.dispose();
    chart = echarts.init(el, 'dark', { renderer: 'canvas' });

    let color = '#eab308';
    if (total >= 70) color = '#10b981';
    else if (total < 30) color = '#ef4444';
    else if (total < 50) color = '#f97316';

    const option = {
        backgroundColor: 'transparent',
        series: [{
            type: 'gauge',
            startAngle: 200,
            endAngle: -20,
            min: 0,
            max: 100,
            splitNumber: 10,
            radius: '90%',
            itemStyle: { color: color },
            progress: { show: true, width: 18 },
            pointer: { show: false },
            axisLine: { lineStyle: { width: 18, color: [[1, '#1e293b']] } },
            axisTick: { show: false },
            splitLine: { show: false },
            axisLabel: { show: false },
            anchor: { show: false },
            title: { show: false },
            detail: {
                valueAnimation: true,
                fontSize: 36,
                fontWeight: 'bold',
                color: color,
                offsetCenter: [0, '10%'],
                formatter: '{value}'
            },
            data: [{ value: total }]
        }]
    };
    chart.setOption(option);
    window.addEventListener('resize', () => chart.resize());
}

function renderScoreRadar(details) {
    const el = document.getElementById('radar-chart');
    let chart = echarts.getInstanceByDom(el);
    if (chart) chart.dispose();
    chart = echarts.init(el, 'dark', { renderer: 'canvas' });

    const dims = [
        { name: 'KD動能', key: 'kd' },
        { name: 'RSI', key: 'rsi' },
        { name: '均線乖離', key: 'ma_bias' },
        { name: 'MACD', key: 'macd' },
        { name: '量價', key: 'volume_price' },
        { name: '趨勢', key: 'trend' },
    ];
    const values = dims.map(d => (details[d.key] || {}).score || 50);

    const option = {
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item' },
        radar: {
            indicator: dims.map(d => ({ name: d.name, max: 100 })),
            shape: 'polygon',
            splitNumber: 4,
            axisName: { color: '#94a3b8', fontSize: 11 },
            splitLine: { lineStyle: { color: '#334155' } },
            splitArea: { show: true, areaStyle: { color: ['#0f172a', '#1e293b'] } },
            axisLine: { lineStyle: { color: '#334155' } }
        },
        series: [{
            type: 'radar',
            data: [{
                value: values,
                name: '綜合評分',
                areaStyle: { color: 'rgba(99, 102, 241, 0.3)' },
                lineStyle: { color: '#6366f1', width: 2 },
                itemStyle: { color: '#6366f1' },
                symbol: 'circle',
                symbolSize: 6
            }]
        }]
    };
    chart.setOption(option);
    window.addEventListener('resize', () => chart.resize());
}

function renderRawMetrics(raw) {
    const metrics = [
        { key: 'rsi', label: 'RSI', fmt: v => v !== null && v !== undefined ? v.toFixed(1) : '-' },
        { key: 'ma20', label: 'MA20', fmt: v => v !== null && v !== undefined ? v.toFixed(2) : '-' },
        { key: 'ma60', label: 'MA60', fmt: v => v !== null && v !== undefined ? v.toFixed(2) : '-' },
        { key: 'macd_hist', label: 'MACD', fmt: v => v !== null && v !== undefined ? v.toFixed(3) : '-' },
        { key: 'volume_ratio', label: '量比', fmt: v => v !== null && v !== undefined ? v.toFixed(2) + 'x' : '-' },
        { key: 'slope_20d', label: '20日斜率', fmt: v => v !== null && v !== undefined ? v.toFixed(2) + '%' : '-' },
    ];
    let html = '';
    metrics.forEach(m => {
        const val = raw[m.key];
        html += `
            <div class="dark-card rounded p-2 border border-dark-border text-center">
                <p class="text-[10px] text-dark-text2">${m.label}</p>
                <p class="text-sm font-mono font-bold text-white">${m.fmt(val)}</p>
            </div>
        `;
    });
    document.getElementById('raw-metrics').innerHTML = html;
}

function renderScoreSummary(score) {
    const total = score.total || 50;
    const rec = score.recommendation || '\u89c0\u671b';
    const d = score.details || {};
    const kd = d.kd || {};
    const rsi = d.rsi || {};
    const macd = d.macd || {};
    const trend = d.trend || {};
    const vp = d.volume_price || {};
    const ma = d.ma_bias || {};

    // Identify strengths (>=70)
    const strengths = [];
    if ((kd.score || 0) >= 70) strengths.push({ label: 'KD\u52d5\u80fd', score: kd.score, detail: `K=${fmt(kd.k)} / D=${fmt(kd.d)}` });
    if ((rsi.score || 0) >= 70) strengths.push({ label: 'RSI\u5f37\u5f31', score: rsi.score, detail: `RSI=${fmt(rsi.value)}` });
    if ((macd.score || 0) >= 70) strengths.push({ label: 'MACD\u8da8\u52e2', score: macd.score, detail: `\u67f1\u72c0\u9ad4=${fmt(macd.macd_hist)}` });
    if ((vp.score || 0) >= 70) strengths.push({ label: '\u91cf\u50f9\u7d50\u69cb', score: vp.score, detail: `\u91cf\u6bd4=${fmt(vp.volume_ratio)}x / \u6f32\u8dcc=${fmt(vp.price_change)}%` });
    if ((trend.score || 0) >= 70) strengths.push({ label: '\u8da8\u52e2\u52d5\u80fd', score: trend.score, detail: `20\u65e5\u659c\u7387=${fmt(trend.slope_20d)}%` });
    if ((ma.score || 0) >= 70) strengths.push({ label: '\u5747\u7dda\u4e56\u96e2', score: ma.score, detail: `MA20\u4e56\u96e2=${fmt(ma.bias20)}%` });

    // Identify weaknesses (<50)
    const weaknesses = [];
    if ((kd.score || 50) < 50) weaknesses.push({ label: 'KD\u52d5\u80fd', score: kd.score, detail: `K=${fmt(kd.k)} / D=${fmt(kd.d)}` });
    if ((rsi.score || 50) < 50) weaknesses.push({ label: 'RSI\u5f37\u5f31', score: rsi.score, detail: `RSI=${fmt(rsi.value)}` });
    if ((macd.score || 50) < 50) weaknesses.push({ label: 'MACD\u8da8\u52e2', score: macd.score, detail: `\u67f1\u72c0\u9ad4=${fmt(macd.macd_hist)}` });
    if ((vp.score || 50) < 50) weaknesses.push({ label: '\u91cf\u50f9\u7d50\u69cb', score: vp.score, detail: `\u91cf\u6bd4=${fmt(vp.volume_ratio)}x / \u6f32\u8dcc=${fmt(vp.price_change)}%` });
    if ((trend.score || 50) < 50) weaknesses.push({ label: '\u8da8\u52e2\u52d5\u80fd', score: trend.score, detail: `20\u65e5\u659c\u7387=${fmt(trend.slope_20d)}%` });
    if ((ma.score || 50) < 50) weaknesses.push({ label: '\u5747\u7dda\u4e56\u96e2', score: ma.score, detail: `MA20\u4e56\u96e2=${fmt(ma.bias20)}%` });

    // Recommendation color
    let recColor = 'text-yellow-400';
    if (total >= 70) recColor = 'text-emerald-400';
    else if (total < 30) recColor = 'text-red-400';
    else if (total < 50) recColor = 'text-orange-400';

    // Build narrative
    let narrative = '';
    let strategy = '';
    let strategyColor = 'text-dark-text2';

    // Determine pattern type based on strengths/weaknesses
    const hasKD = strengths.some(s => s.label === 'KD\u52d5\u80fd');
    const hasRSI = strengths.some(s => s.label === 'RSI\u5f37\u5f31');
    const hasMACD = strengths.some(s => s.label === 'MACD\u8da8\u52e2');
    const hasTrend = strengths.some(s => s.label === '\u8da8\u52e2\u52d5\u80fd');
    const hasMA = strengths.some(s => s.label === '\u5747\u7dda\u4e56\u96e2');
    const hasVP = strengths.some(s => s.label === '\u91cf\u50f9\u7d50\u69cb');
    const weakTrend = weaknesses.some(w => w.label === '\u8da8\u52e2\u52d5\u80fd');
    const weakKD = weaknesses.some(w => w.label === 'KD\u52d5\u80fd');
    const weakMACD = weaknesses.some(w => w.label === 'MACD\u8da8\u52e2');
    const weakRSI = weaknesses.some(w => w.label === 'RSI\u5f37\u5f31');
    const weakMA = weaknesses.some(w => w.label === '\u5747\u7dda\u4e56\u96e2');

    // Pattern-based narrative and strategy
    if (total >= 80) {
        narrative = '\u591a\u500b\u6280\u8853\u6307\u6a19\u540c\u6b65\u767c\u51fa\u5f37\u52e3\u8cb7\u5165\u8a0a\u865f\uff0c\u4e0b\u884c\u98a8\u96aa\u8f03\u4f4e\uff0c\u9069\u5408\u7a4d\u6975\u4f48\u5c40\u3002';
        strategy = '\u64cd\u4f5c\u7b56\u7565\uff1a\u8d95\u52e2\u6301\u6709\uff0c\u56de\u8abf\u6642\u53ef\u8003\u616e\u52a0\u78bc\u3002\u5efa\u8b70\u7528\u5747\u7dda\u6216\u524d\u4f4e\u505c\u5229\u591a\u55ae\u4fdd\u8b77\u5229\u76ca\u3002';
        strategyColor = 'text-emerald-400';
    } else if (total >= 60) {
        if ((hasKD || hasRSI) && weakTrend) {
            // Oversold bounce
            narrative = '\u6280\u8853\u6307\u6a19\u986f\u793a\u56b4\u91cd\u8d85\u8ce3\uff0c\u77ed\u7dda\u53cd\u5f48\u6a5f\u6703\u9ad8\uff0c\u4f46\u4e2d\u9577\u671f\u8da8\u52e2\u4ecd\u5f31\u3002';
            strategy = '\u64cd\u4f5c\u7b56\u7565\uff1a\u5206\u6279\u4f4e\u63a5\u8a66\u55ae\uff0c\u55ae\u7b46\u5009\u4f4d\u4e0d\u8d85\u904e 20%\u3002\u8a2d\u5b9a\u7dca\u8cbc\u7684\u505c\u640d\u9ede\uff08\u524d\u4f4e -5% ~ -7%\uff09\uff0c\u53cd\u5f48\u81f3\u5747\u7dda\u9644\u8fd1\u82e5\u7121\u529b\u7a7f\u8d8a\u53ef\u7372\u5229\u4e86\u7d50\u3002';
            strategyColor = 'text-emerald-400';
        } else if (hasTrend && (hasMACD || hasKD)) {
            narrative = '\u8da8\u52e2\u8f49\u5f37\uff0c\u6280\u8853\u6307\u6a19\u540c\u6b65\u6539\u5584\uff0c\u9032\u5834\u8f03\u70ba\u5b89\u5168\u3002';
            strategy = '\u64cd\u4f5c\u7b56\u7565\uff1a\u56de\u8abf\u81f3\u652f\u6490\u5340\u53ef\u52a0\u78bc\uff0c\u4ee5 20 \u65e5\u5747\u7dda\u70ba\u6b62\u640d\u53c3\u8003\u3002';
            strategyColor = 'text-emerald-400';
        } else {
            narrative = '\u90e8\u5206\u6307\u6a19\u986f\u793a\u8cb7\u9032\u6a5f\u6703\uff0c\u4f46\u4ecd\u6709\u4e0d\u78ba\u5b9a\u56e0\u7d20\uff0c\u5efa\u8b70\u5206\u6279\u9032\u5834\u3002';
            strategy = '\u64cd\u4f5c\u7b56\u7565\uff1a\u5c0f\u5009\u8a66\u55ae\uff0c\u7b49\u5f85\u66f4\u591a\u6307\u6a19\u8f49\u5f37\u5f8c\u518d\u52a0\u78bc\u3002';
            strategyColor = 'text-yellow-400';
        }
    } else if (total >= 40) {
        if (weakTrend && weakMACD) {
            narrative = '\u8da8\u52e2\u8207 MACD \u540c\u6b65\u8f49\u5f31\uff0c\u591a\u7a7a\u96d9\u65b9\u6301\u7e8c\u62c9\u92f2\uff0c\u5e02\u5834\u65b9\u5411\u4e0d\u660e\u3002';
            strategy = '\u64cd\u4f5c\u7b56\u7565\uff1a\u7e7c\u7e8c\u89c0\u5bdf\uff0c\u907f\u514d\u91cd\u5009\u9032\u5834\u3002\u53ef\u8003\u616e\u7528\u5c11\u91cf\u8cc7\u91d1\u9032\u884c\u77ed\u7dda\u64cd\u4f5c\uff0c\u8a2d\u5b9a\u6b62\u640d\u6b62\u76c8\u3002';
            strategyColor = 'text-yellow-400';
        } else {
            narrative = '\u591a\u7a7a\u96d9\u65b9\u52d5\u80fd\u5e73\u8861\uff0c\u5e02\u5834\u65b9\u5411\u4e0d\u660e\uff0c\u5efa\u8b70\u7e7c\u7e8c\u89c0\u5bdf\u3002';
            strategy = '\u64cd\u4f5c\u7b56\u7565\uff1a\u6301\u7e8c\u95dc\u6ce8\uff0c\u7b49\u5f85\u660e\u78ba\u8a0a\u865f\u51fa\u73fe\u3002';
            strategyColor = 'text-yellow-400';
        }
    } else if (total >= 20) {
        if (weakKD && weakRSI && weakTrend) {
            narrative = '\u591a\u500b\u6307\u6a19\u540c\u6b65\u8f49\u5f31\uff0c\u4e0a\u884c\u58d3\u529b\u5927\uff0c\u4e0b\u884c\u98a8\u96aa\u8f03\u9ad8\u3002';
            strategy = '\u64cd\u4f5c\u7b56\u7565\uff1a\u964d\u4f4e\u5009\u4f4d\u81f3 50% \u4ee5\u4e0b\uff0c\u6216\u7b49\u5f85\u66f4\u660e\u78ba\u7684\u8cb7\u9ede\u51fa\u73fe\u3002\u82e5\u5df2\u6301\u6709\uff0c\u53ef\u8003\u616e\u5229\u7528\u9078\u64c7\u6b0a\u6216\u8f49\u63db\u8cc7\u7522\u9032\u884c\u6aa2\u6e2c\u3002';
            strategyColor = 'text-orange-400';
        } else if (weakTrend) {
            narrative = '\u8da8\u52e2\u8f49\u5f31\uff0c\u90e8\u5206\u6307\u6a19\u986f\u793a\u8ce6\u50f9\u58d3\u529b\uff0c\u4e0b\u884c\u98a8\u96aa\u8f03\u5927\u3002';
            strategy = '\u64cd\u4f5c\u7b56\u7565\uff1a\u964d\u4f4e\u5009\u4f4d\uff0c\u907f\u514d\u8ffd\u6f32\u3002\u7b49\u5f85 KD \u6216 RSI \u9032\u5165\u8d85\u8ce3\u5340\u5f8c\u518d\u8003\u616e\u9032\u5834\u3002';
            strategyColor = 'text-orange-400';
        } else {
            narrative = '\u90e8\u5206\u6307\u6a19\u986f\u793a\u8ce6\u50f9\u58d3\u529b\uff0c\u4e0b\u884c\u98a8\u96aa\u8f03\u5927\uff0c\u5efa\u8b70\u964d\u4f4e\u5009\u4f4d\u6216\u7b49\u5f85\u66f4\u660e\u78ba\u8a0a\u865f\u3002';
            strategy = '\u64cd\u4f5c\u7b56\u7565\uff1a\u6e1b\u5c11\u6301\u80a1\uff0c\u4fdd\u6301\u73fe\u91d1\u6c34\u4f4d\u3002';
            strategyColor = 'text-orange-400';
        }
    } else {
        narrative = '\u591a\u500b\u6280\u8853\u6307\u6a19\u540c\u6b65\u767c\u51fa\u8ce6\u50f9\u8a0a\u865f\uff0c\u4e0b\u884c\u98a8\u96aa\u9ad8\uff0c\u5efa\u8b70\u56b4\u683c\u63a7\u7ba1\u98a8\u96aa\u3002';
        strategy = '\u64cd\u4f5c\u7b56\u7565\uff1a\u7a7a\u5009\u89c0\u671b\u70ba\u4e3b\uff0c\u6216\u8003\u616e\u9006\u5411\u64cd\u4f5c\u5de5\u5177\uff08\u5982\u653e\u7a7a\u3001\u8cb7\u8ce4\u9078\u64c7\u6b0a\uff09\u3002\u5df2\u6301\u6709\u8005\u61c9\u8a55\u4f30\u505c\u640d\u6216\u9000\u5834\u6a5f\u5236\u3002';
        strategyColor = 'text-red-400';
    }

    let html = `
        <div class="dark-card rounded-lg border border-dark-border p-4">
            <p class="text-base font-bold ${recColor} mb-2">${rec}\uff08${total}\u5206\uff09</p>
            <p class="text-dark-text mb-2">${narrative}</p>
            <p class="${strategyColor} mb-3 border-l-2 pl-3" style="border-color: currentColor;">${strategy}</p>
    `;

    if (strengths.length > 0) {
        html += `<div class="mb-3"><p class="text-xs font-semibold text-emerald-400 mb-1"><i class="fas fa-arrow-up mr-1"></i>\u5f37\u9805</p><div class="space-y-1">`;
        strengths.forEach(s => {
            html += `<div class="flex justify-between text-xs"><span class="text-dark-text2">${s.label} <span class="text-dark-text3 opacity-60">(${s.detail})</span></span><span class="font-mono font-bold text-emerald-400">${s.score}</span></div>`;
        });
        html += `</div></div>`;
    }

    if (weaknesses.length > 0) {
        html += `<div><p class="text-xs font-semibold text-red-400 mb-1"><i class="fas fa-arrow-down mr-1"></i>\u5f31\u9805</p><div class="space-y-1">`;
        weaknesses.forEach(w => {
            html += `<div class="flex justify-between text-xs"><span class="text-dark-text2">${w.label} <span class="text-dark-text3 opacity-60">(${w.detail})</span></span><span class="font-mono font-bold text-red-400">${w.score}</span></div>`;
        });
        html += `</div></div>`;
    }

    html += `</div>`;
    document.getElementById('score-summary').innerHTML = html;
}

function fmt(v) {
    if (v === null || v === undefined) return '-';
    if (typeof v === 'number') {
        if (Math.abs(v) >= 100) return v.toFixed(1);
        if (Math.abs(v) >= 1) return v.toFixed(2);
        return v.toFixed(3);
    }
    return v;
}
