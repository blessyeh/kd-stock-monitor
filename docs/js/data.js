/**
 * Data Module - Handles data loading and management
 */

// Sample data structure for development/fallback
const SAMPLE_DATA = {
    "TW": [
        {
            "symbol": "0050.TW",
            "name": "元大台灣50",
            "market": "TW",
            "current_price": 145.5,
            "kd_k": 75.5,
            "kd_d": 72.3,
            "bias_5": 1.2,
            "bias_10": -0.5,
            "bias_20": -2.1,
            "last_updated": new Date().toISOString(),
            "history": []
        },
        {
            "symbol": "0056.TW",
            "name": "元大高股息",
            "market": "TW",
            "current_price": 32.8,
            "kd_k": 82.1,
            "kd_d": 80.5,
            "last_updated": new Date().toISOString(),
            "history": []
        },
        {
            "symbol": "2330.TW",
            "name": "台積電",
            "market": "TW",
            "current_price": 550.0,
            "kd_k": 15.2,
            "kd_d": 18.7,
            "last_updated": new Date().toISOString(),
            "history": []
        },
        {
            "symbol": "2317.TW",
            "name": "鴻海",
            "market": "TW",
            "current_price": 105.5,
            "kd_k": 45.0,
            "kd_d": 48.2,
            "last_updated": new Date().toISOString(),
            "history": []
        },
        {
            "symbol": "2454.TW",
            "name": "聯發科",
            "market": "TW",
            "current_price": 890.0,
            "kd_k": 85.3,
            "kd_d": 81.2,
            "last_updated": new Date().toISOString(),
            "history": []
        }
    ],
    "US": [
        {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "market": "US",
            "current_price": 175.5,
            "kd_k": 12.5,
            "kd_d": 15.8,
            "last_updated": new Date().toISOString(),
            "history": []
        },
        {
            "symbol": "TSLA",
            "name": "Tesla Inc.",
            "market": "US",
            "current_price": 240.0,
            "kd_k": 78.2,
            "kd_d": 75.5,
            "last_updated": new Date().toISOString(),
            "history": []
        },
        {
            "symbol": "MSFT",
            "name": "Microsoft Corp.",
            "market": "US",
            "current_price": 380.5,
            "kd_k": 68.5,
            "kd_d": 65.2,
            "last_updated": new Date().toISOString(),
            "history": []
        },
        {
            "symbol": "GOOGL",
            "name": "Alphabet Inc.",
            "market": "US",
            "current_price": 142.8,
            "kd_k": 88.5,
            "kd_d": 85.3,
            "last_updated": new Date().toISOString(),
            "history": []
        },
        {
            "symbol": "NVDA",
            "name": "NVIDIA Corp.",
            "market": "US",
            "current_price": 495.0,
            "kd_k": 25.3,
            "kd_d": 28.7,
            "last_updated": new Date().toISOString(),
            "history": []
        }
    ],
    "last_updated": new Date().toISOString()
};

const SAMPLE_ALERTS = [
    {
        "id": "0056.TW_20240321_overbought",
        "symbol": "0056.TW",
        "name": "元大高股息",
        "market": "TW",
        "type": "overbought",
        "level": "high",
        "kd_k": 82.1,
        "kd_d": 80.5,
        "current_price": 32.8,
        "threshold": 80,
        "message": "⚠️ 0056.TW (元大高股息) is OVERBOUGHT! KD-K: 82.1, KD-D: 80.5",
        "timestamp": new Date().toISOString(),
        "date": new Date().toISOString().split('T')[0],
        "acknowledged": false
    },
    {
        "id": "2330.TW_20240321_oversold",
        "symbol": "2330.TW",
        "name": "台積電",
        "market": "TW",
        "type": "oversold",
        "level": "low",
        "kd_k": 15.2,
        "kd_d": 18.7,
        "current_price": 550.0,
        "threshold": 20,
        "message": "✅ 2330.TW (台積電) is OVERSOLD! KD-K: 15.2, KD-D: 18.7",
        "timestamp": new Date().toISOString(),
        "date": new Date().toISOString().split('T')[0],
        "acknowledged": false
    },
    {
        "id": "AAPL_20240321_oversold",
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "market": "US",
        "type": "oversold",
        "level": "low",
        "kd_k": 12.5,
        "kd_d": 15.8,
        "current_price": 175.5,
        "threshold": 20,
        "message": "✅ AAPL (Apple Inc.) is OVERSOLD! KD-K: 12.5, KD-D: 15.8",
        "timestamp": new Date().toISOString(),
        "date": new Date().toISOString().split('T')[0],
        "acknowledged": false
    },
    {
        "id": "GOOGL_20240321_overbought",
        "symbol": "GOOGL",
        "name": "Alphabet Inc.",
        "market": "US",
        "type": "overbought",
        "level": "high",
        "kd_k": 88.5,
        "kd_d": 85.3,
        "current_price": 142.8,
        "threshold": 80,
        "message": "⚠️ GOOGL (Alphabet Inc.) is OVERBOUGHT! KD-K: 88.5, KD-D: 85.3",
        "timestamp": new Date().toISOString(),
        "date": new Date().toISOString().split('T')[0],
        "acknowledged": false
    }
];

const SAMPLE_SUMMARY = {
    "timestamp": new Date().toISOString(),
    "date": new Date().toISOString().split('T')[0],
    "stocks_processed": 10,
    "stocks_successful": 10,
    "stocks_failed": 0,
    "new_alerts": 4,
    "overbought_count": 2,
    "oversold_count": 2,
    "normal_count": 6,
    "overbought_stocks": [
        {"symbol": "0056.TW", "name": "元大高股息", "kd_k": 82.1, "kd_d": 80.5},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "kd_k": 88.5, "kd_d": 85.3}
    ],
    "oversold_stocks": [
        {"symbol": "2330.TW", "name": "台積電", "kd_k": 15.2, "kd_d": 18.7},
        {"symbol": "AAPL", "name": "Apple Inc.", "kd_k": 12.5, "kd_d": 15.8}
    ],
    "errors": []
};

// Data Manager
const DataManager = {
    stockData: null,
    alerts: null,
    summary: null,
    loadError: false,
    errorMessage: '',
    
    /**
     * Load all data from JSON files.
     * Does NOT fallback to sample data on failure — shows error instead.
     */
    async loadData() {
        this.loadError = false;
        this.errorMessage = '';
        
        try {
            // Try to load from data files
            // Note: When deployed to GitHub Pages, data is copied to docs/data/
            // Use 'no-cache' (conditional revalidation via ETag/Last-Modified) instead of a
            // random cache-busting query string — this still always gets fresh data logically,
            // but lets the browser skip re-downloading the ~750KB payload via a 304 when
            // the file hasn't actually changed (huge win for the 5-minute auto-refresh).
            const fetchOpts = { cache: 'no-cache' };
            const stockResponse = await fetch(`./data/stock_data.json`, fetchOpts);
            const alertsResponse = await fetch(`./data/alerts.json`, fetchOpts);
            const summaryResponse = await fetch(`./data/summary.json`, fetchOpts);
            
            if (stockResponse.ok) {
                this.stockData = await stockResponse.json();
            } else {
                console.error(`Failed to load stock_data.json: HTTP ${stockResponse.status}`);
                this.loadError = true;
                this.errorMessage = `股票數據加載失敗 (HTTP ${stockResponse.status})`;
                this.stockData = { "TW": [], "US": [], "last_updated": new Date().toISOString() };
            }
            
            if (alertsResponse.ok) {
                this.alerts = await alertsResponse.json();
            } else {
                console.error(`Failed to load alerts.json: HTTP ${alertsResponse.status}`);
                this.alerts = [];
            }
            
            if (summaryResponse.ok) {
                this.summary = await summaryResponse.json();
            } else {
                console.error(`Failed to load summary.json: HTTP ${summaryResponse.status}`);
                this.summary = {
                    "timestamp": new Date().toISOString(),
                    "date": new Date().toISOString().split('T')[0],
                    "stocks_processed": 0,
                    "stocks_successful": 0,
                    "stocks_failed": 0,
                    "new_alerts": 0,
                    "overbought_count": 0,
                    "oversold_count": 0,
                    "normal_count": 0,
                    "overbought_stocks": [],
                    "oversold_stocks": [],
                    "errors": []
                };
            }
            
        } catch (error) {
            console.error('Error loading data:', error);
            this.loadError = true;
            this.errorMessage = `數據加載異常: ${error.message}`;
            this.stockData = { "TW": [], "US": [], "last_updated": new Date().toISOString() };
            this.alerts = [];
            this.summary = {
                "timestamp": new Date().toISOString(),
                "date": new Date().toISOString().split('T')[0],
                "stocks_processed": 0,
                "stocks_successful": 0,
                "stocks_failed": 0,
                "new_alerts": 0,
                "overbought_count": 0,
                "oversold_count": 0,
                "normal_count": 0,
                "overbought_stocks": [],
                "oversold_stocks": [],
                "errors": []
            };
        }
        
        return {
            stockData: this.stockData,
            alerts: this.alerts,
            summary: this.summary,
            loadError: this.loadError,
            errorMessage: this.errorMessage
        };
    },
    
    /**
     * Get all stocks as a flat array
     */
    getAllStocks() {
        if (!this.stockData) return [];
        const stocks = [
            ...(this.stockData.TW || []),
            ...(this.stockData.US || [])
        ];
        return stocks.sort((a, b) => {
            const aVal = a.kd_k !== null && a.kd_k !== undefined ? a.kd_k : Infinity;
            const bVal = b.kd_k !== null && b.kd_k !== undefined ? b.kd_k : Infinity;
            return aVal - bVal;
        });
    },
    
    /**
     * Get stocks by market
     */
    getStocksByMarket(market) {
        if (!this.stockData) return [];
        const stocks = this.stockData[market] || [];
        return stocks.sort((a, b) => {
            const aVal = a.kd_k !== null && a.kd_k !== undefined ? a.kd_k : Infinity;
            const bVal = b.kd_k !== null && b.kd_k !== undefined ? b.kd_k : Infinity;
            return aVal - bVal;
        });
    },
    
    /**
     * Get alert stocks only
     */
    getAlertStocks() {
        return this.getAllStocks().filter(stock => {
            if (stock.kd_k === null || stock.kd_k === undefined) return false;
            return stock.kd_k >= 80 || stock.kd_k <= 20 ||
                   (stock.kd_d !== null && (stock.kd_d >= 80 || stock.kd_d <= 20));
        });
    },
    
    /**
     * Get stock by symbol
     */
    getStock(symbol) {
        return this.getAllStocks().find(s => s.symbol === symbol);
    },
    
    /**
     * Get alerts
     */
    getAlerts(limit = null) {
        if (!this.alerts) return [];
        const alerts = Array.isArray(this.alerts) ? this.alerts : [];
        return limit ? alerts.slice(0, limit) : alerts;
    },
    
    /**
     * Get summary
     */
    getSummary() {
        return this.summary || SAMPLE_SUMMARY;
    },
    
    /**
     * Get KD status for a stock
     */
    getKDStatus(kd_k, kd_d) {
        if (kd_k === null || kd_k === undefined) return 'normal';
        if (kd_k >= 80 || (kd_d !== null && kd_d >= 80)) return 'overbought';
        if (kd_k <= 20 || (kd_d !== null && kd_d <= 20)) return 'oversold';
        return 'normal';
    },
    
    /**
     * Format date (convert UTC to Taiwan time)
     */
    formatDate(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        // Convert to Taiwan time (UTC+8)
        const taiwanDate = new Date(date.getTime() + (8 * 60 * 60 * 1000));
        return taiwanDate.toLocaleString('zh-TW', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            timeZone: 'UTC'
        });
    },
    
    /**
     * Format price
     */
    formatPrice(price, currency = 'USD') {
        if (price === null || price === undefined) return '-';
        const symbol = currency === 'TWD' ? 'NT$' : '$';
        return `${symbol}${price.toFixed(2)}`;
    },

    /**
     * Load historical data from _kd.csv for a specific stock
     */
    async loadStockHistory(symbol) {
        try {
            const fileName = symbol.replace(/\./g, '_') + '_kd.csv';
            const response = await fetch(`./data/${fileName}`, { cache: 'no-cache' });
            if (!response.ok) {
                console.log(`History file not found for ${symbol}: ${fileName}`);
                return null;
            }
            const csvText = await response.text();
            const lines = csvText.trim().split('\n');
            if (lines.length < 2) return null;

            const headers = lines[0].split(',');
            const history = [];
            for (let i = 1; i < lines.length; i++) {
                const values = lines[i].split(',');
                if (values.length < 10) continue;
                const row = {};
                headers.forEach((h, idx) => { row[h.trim()] = values[idx]?.trim(); });

                const item = {
                    date: row.date,
                    open: parseFloat(row.open),
                    high: parseFloat(row.high),
                    low: parseFloat(row.low),
                    close: parseFloat(row.close),
                    volume: parseFloat(row.volume) || 0,
                    kd_k: parseFloat(row.kd_k),
                    kd_d: parseFloat(row.kd_d),
                    bias_5: parseFloat(row.bias_5) || null,
                    bias_10: parseFloat(row.bias_10) || null,
                    bias_20: parseFloat(row.bias_20) || null
                };
                // Skip rows with invalid data
                if (!isNaN(item.close) && !isNaN(item.kd_k) && item.date) {
                    history.push(item);
                }
            }
            // Sort by date ascending
            history.sort((a, b) => new Date(a.date) - new Date(b.date));
            console.log(`Loaded ${history.length} history records for ${symbol}`);
            return history;
        } catch (error) {
            console.warn(`Error loading history for ${symbol}:`, error);
            return null;
        }
    }
};