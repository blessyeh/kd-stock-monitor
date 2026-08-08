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
 * Initialize the application
 */
document.addEventListener('DOMContentLoaded', async () => {
    console.log('KD Stock Monitor - Initializing...');

    // Load data
    await DataManager.loadData();

    // Initialize UI
    updateStats();
    updateTaiexSection();
    updateChipStats();
    renderSignalConfluence();
    renderStockGrid();
    renderAlertHistory();
    updateLastUpdated();

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

        // 投信買賣超 (億元)
        const trustEl = document.getElementById('chip-trust');
        if (trustEl && chip.trust_net && chip.trust_net.value !== null && chip.trust_net.value !== undefined) {
            const val = chip.trust_net.value;
            const colorClass = val >= 0 ? 'text-kd-red' : 'text-kd-green';
            const sign = val >= 0 ? '+' : '';
            trustEl.className = `font-bold text-lg mt-1 ${colorClass}`;
            trustEl.textContent = `${sign}${val.toFixed(1)}億`;
        }

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

        // 資券比 (%) — neutral stat, no directional color
        const ratioEl = document.getElementById('chip-ratio');
        if (ratioEl && chip.margin_short_ratio && chip.margin_short_ratio.value !== null && chip.margin_short_ratio.value !== undefined) {
            ratioEl.className = 'font-bold text-lg mt-1 text-dark-text';
            ratioEl.textContent = `${chip.margin_short_ratio.value.toFixed(2)}%`;
        }

        // 新台幣匯率 (USD/TWD) — same up/down convention as the DXY card
        const twdEl = document.getElementById('chip-twd');
        if (twdEl && chip.usdtwd && chip.usdtwd.value !== null && chip.usdtwd.value !== undefined) {
            const val = chip.usdtwd.value;
            const change = chip.usdtwd.change || 0;
            const colorClass = change >= 0 ? 'text-kd-red' : 'text-kd-green';
            twdEl.className = `font-bold text-lg mt-1 ${colorClass}`;
            twdEl.textContent = val.toFixed(3);
        }

        // 外資期貨淨部位 (口) — positive = net long = red, negative = net short = green
        const futuresEl = document.getElementById('chip-futures');
        if (futuresEl && chip.foreign_futures_net && chip.foreign_futures_net.value !== null && chip.foreign_futures_net.value !== undefined) {
            const val = chip.foreign_futures_net.value;
            const colorClass = val >= 0 ? 'text-kd-red' : 'text-kd-green';
            const sign = val >= 0 ? '+' : '';
            futuresEl.className = `font-bold text-lg mt-1 ${colorClass}`;
            futuresEl.textContent = `${sign}${val.toLocaleString()}口`;
        }

        // 選擇權 Put/Call Ratio (%) — neutral stat, no directional color
        const pcRatioEl = document.getElementById('chip-pcratio');
        if (pcRatioEl && chip.put_call_ratio && chip.put_call_ratio.value !== null && chip.put_call_ratio.value !== undefined) {
            pcRatioEl.className = 'font-bold text-lg mt-1 text-dark-text';
            pcRatioEl.textContent = `${chip.put_call_ratio.value.toFixed(2)}%`;
        }
    } catch (e) {
        console.error("Error updating chip stats:", e);
    }
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
 * Create alert item HTML
 */
function createAlertItem(alert) {
    const typeClass = alert.type === 'overbought' ? 'overbought' : 'oversold';
    const icon = alert.type === 'overbought' ? 'fa-arrow-up text-kd-red' : 'fa-arrow-down text-kd-green';
    const title = alert.type === 'overbought' ? '超買警告' : '超賣提醒';

    return `
        <div class="alert-item ${typeClass} ${alert.acknowledged ? 'acknowledged' : ''}">
            <div class="flex-shrink-0 mr-3">
                <i class="fas ${icon} text-xl"></i>
            </div>
            <div class="flex-grow">
                <div class="flex justify-between items-start">
                    <div>
                        <span class="font-semibold text-white">${alert.symbol}</span>
                        <span class="text-sm text-dark-text2 ml-1">${alert.name}</span>
                        <span class="ml-2 px-2 py-0.5 rounded text-xs ${alert.type === 'overbought' ? 'bg-red-900/30 text-kd-red' : 'bg-green-900/30 text-kd-green'}">
                            ${title}
                        </span>
                    </div>
                    <span class="text-xs text-dark-text2">${DataManager.formatDate(alert.timestamp)}</span>
                </div>
                <div class="mt-1 text-sm text-dark-text2">
                    KD-K: <span class="font-semibold text-white">${alert.kd_k}</span> |
                    KD-D: <span class="font-semibold text-white">${alert.kd_d}</span> |
                    價格: <span class="font-semibold text-white">${DataManager.formatPrice(alert.current_price, alert.market === 'TW' ? 'TWD' : 'USD')}</span>
                </div>
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
    updateChipStats();
    renderSignalConfluence();
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
