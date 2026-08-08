#!/usr/bin/env python3
"""
Stock Data Fetcher - Fetches stock data from Yahoo Finance for TW and US stocks.
Supports incremental updates to reduce API calls.
"""

import yfinance as yf
import pandas as pd
import requests
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class StockFetcher:
    """Fetches historical stock data from Yahoo Finance with incremental update support."""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize with configuration."""
        self.config = self._load_config(config_path)
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file."""
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _get_raw_filepath(self, symbol: str) -> str:
        """Get the filepath for raw stock data CSV."""
        return os.path.join(self.data_dir, f"{symbol.replace('.', '_')}_raw.csv")
    
    def _load_local_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Load existing local raw data for a symbol if available.
        
        Returns:
            DataFrame with existing data or None if not found
        """
        filepath = self._get_raw_filepath(symbol)
        if not os.path.exists(filepath):
            return None
        
        try:
            df = pd.read_csv(filepath)
            if df.empty:
                return None
            
            # Ensure date column is datetime
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            
            logger.info(f"Loaded {len(df)} local records for {symbol} (last: {df['date'].iloc[-1].date()})")
            return df
        except Exception as e:
            logger.warning(f"Error loading local data for {symbol}: {e}")
            return None
    
    def _merge_data(self, old_df: pd.DataFrame, new_df: pd.DataFrame, symbol: str = "") -> pd.DataFrame:
        """
        Merge old and new DataFrames, removing duplicates by date.
        Also drops rows with NaN in any OHLC price column.
        If the latest row in new_df has NaN prices, attempts to fill from ticker.info.
        """
        # Ensure date columns are datetime
        for df in [old_df, new_df]:
            if 'date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['date']):
                df['date'] = pd.to_datetime(df['date'])
        
        # Attempt to repair NaN rows in new_df using ticker.info before dropping
        if not new_df.empty and symbol:
            last_idx = new_df.index[-1]
            price_cols = ['open', 'high', 'low', 'close']
            if new_df.loc[last_idx, price_cols].isna().all():
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    # Build a repair map from info fields
                    repair = {}
                    if info.get('regularMarketOpen') is not None:
                        repair['open'] = info['regularMarketOpen']
                    if info.get('regularMarketDayHigh') is not None:
                        repair['high'] = info['regularMarketDayHigh']
                    if info.get('regularMarketDayLow') is not None:
                        repair['low'] = info['regularMarketDayLow']
                    if info.get('regularMarketPrice') is not None:
                        repair['close'] = info['regularMarketPrice']
                    if info.get('regularMarketVolume') is not None:
                        repair['volume'] = info['regularMarketVolume']
                    if repair:
                        for col, val in repair.items():
                            if col in new_df.columns:
                                new_df.loc[last_idx, col] = val
                        logger.info(f"[{symbol}] Repaired NaN latest row from info: {repair}")
                except Exception as e:
                    logger.warning(f"[{symbol}] Failed to repair NaN latest row from info: {e}")
        
        # Drop rows with NaN in any price column (OHLC)
        price_cols = ['open', 'high', 'low', 'close']
        for df in [old_df, new_df]:
            mask = df[price_cols].notna().all(axis=1)
            dropped = (~mask).sum()
            if dropped > 0:
                logger.warning(f"Dropped {dropped} rows with NaN prices before merge")
            df.drop(df[~mask].index, inplace=True)
        
        # Concatenate and drop duplicates by date, keeping new data
        combined = pd.concat([old_df, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=['date'], keep='last')
        combined = combined.sort_values('date').reset_index(drop=True)
        
        return combined
    
    def fetch_stock_data(self, symbol: str, period: str = "2y", interval: str = "1d") -> Optional[pd.DataFrame]:
        """
        Fetch historical stock data from Yahoo Finance with incremental update support.
        
        Strategy:
        1. Check for existing local data
        2. If local data exists and is recent (< 30 days old), fetch incrementally
        3. If no local data or data is stale, fetch full history
        4. Merge and save combined data
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', '2330.TW')
            period: Default full-fetch period if no local data exists
            interval: Data interval ('1d', '1wk', '1mo')
        
        Returns:
            DataFrame with OHLCV data or None if fetch fails
        """
        # Step 1: Load local data if available
        local_df = self._load_local_data(symbol)
        
        try:
            ticker = yf.Ticker(symbol)
            
            if local_df is not None and not local_df.empty:
                last_local_date = local_df['date'].max()
                days_since_update = (datetime.now() - last_local_date).days
                
                if days_since_update <= 35:
                    # Incremental fetch: fetch from 7 days before last date to handle weekends/holidays
                    fetch_start = (last_local_date - timedelta(days=7)).strftime('%Y-%m-%d')
                    logger.info(f"[{symbol}] Incremental update: fetching from {fetch_start} (local last: {last_local_date.date()}, {days_since_update} days ago)")
                    
                    df_new = ticker.history(start=fetch_start, interval=interval)
                    
                    if df_new.empty:
                        logger.warning(f"No new data returned for {symbol}, using local data only")
                        return local_df
                    
                    # Standardize new data columns
                    df_new = df_new.reset_index()
                    df_new.columns = [col.replace(' ', '_').lower() for col in df_new.columns]
                    if 'date' in df_new.columns and pd.api.types.is_datetime64_any_dtype(df_new['date']):
                        df_new['date'] = df_new['date'].dt.tz_localize(None)
                    
                    # Merge with local data
                    df_merged = self._merge_data(local_df, df_new, symbol)
                    logger.info(f"[{symbol}] Merged: local({len(local_df)}) + new({len(df_new)}) = {len(df_merged)} records")
                    
                    # Save merged data
                    self._save_raw_data(symbol, df_merged)
                    return df_merged
                else:
                    logger.info(f"[{symbol}] Local data is {days_since_update} days old, performing full fetch")
            else:
                logger.info(f"[{symbol}] No local data found, performing full fetch")
            
            # Full fetch (no local data or data too stale)
            logger.info(f"[{symbol}] Fetching full data (period={period})...")
            df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return None
            
            # Reset index to make Date a column
            df = df.reset_index()
            
            # Ensure column names are standardized
            df.columns = [col.replace(' ', '_').lower() for col in df.columns]
            
            # Handle timezone-aware datetime
            if 'date' in df.columns and pd.api.types.is_datetime64_any_dtype(df['date']):
                df['date'] = df['date'].dt.tz_localize(None)
            
            # If we had stale local data, merge it to preserve older history
            if local_df is not None:
                df = self._merge_data(local_df, df, symbol)
            
            # Save raw data
            self._save_raw_data(symbol, df)
            
            logger.info(f"[{symbol}] Full fetch complete: {len(df)} records")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            # Fallback to local data if fetch fails
            if local_df is not None:
                logger.info(f"[{symbol}] Returning local data as fallback")
                return local_df
            return None
    
    def _fetch_one_stock(self, market: str, stock: Dict) -> Tuple[str, Optional[Dict]]:
        """
        Fetch data + extra_data for a single stock. Designed to be safe to run
        from a worker thread: each symbol only touches its own CSV file and its
        own yf.Ticker instance, so there's no shared mutable state between calls.
        """
        symbol = stock["symbol"]
        df = self.fetch_stock_data(symbol)

        if df is None or df.empty:
            logger.warning(f"Failed to fetch data for {symbol}")
            return market, None

        # Get real-time/extended hours data
        extra_data = {}
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            extra_data = {
                "regular_market_price": info.get("regularMarketPrice"),
                "pre_market_price": info.get("preMarketPrice"),
                "post_market_price": info.get("postMarketPrice"),
                "prev_close": info.get("regularMarketPreviousClose")
            }
        except Exception as e:
            logger.error(f"Error fetching extra data for {symbol}: {e}")

        return market, {
            "symbol": symbol,
            "name": stock["name"],
            "market": market,
            "data": df,
            "extra_data": extra_data,
            "last_updated": datetime.now().isoformat()
        }

    def fetch_all_stocks(self, max_workers: int = 5) -> Dict[str, List[Dict]]:
        """
        Fetch data for all configured stocks with incremental update support.

        Fetches run on a small thread pool since each call is network-bound
        (Yahoo Finance HTTP requests) and largely blocked on I/O wait, not CPU.
        max_workers is kept modest by default to avoid tripping Yahoo Finance's
        rate limiting when running ~100+ symbols back to back.

        Returns:
            Dictionary with stock data organized by market
        """
        results = {"TW": [], "US": []}
        tasks = [
            (market, stock)
            for market in ["TW", "US"]
            for stock in self.config["stocks"][market]
        ]

        if not tasks:
            return results

        workers = max(1, min(max_workers, len(tasks)))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_symbol = {
                executor.submit(self._fetch_one_stock, market, stock): stock["symbol"]
                for market, stock in tasks
            }
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    market, entry = future.result()
                    if entry is not None:
                        results[market].append(entry)
                except Exception as e:
                    logger.error(f"Unhandled error fetching {symbol}: {e}")

        # Threads complete out of order; restore the configured symbol order so
        # downstream output (JSON, dashboard ordering) stays deterministic.
        order = {
            market: [s["symbol"] for s in self.config["stocks"][market]]
            for market in ["TW", "US"]
        }
        for market in results:
            results[market].sort(key=lambda s: order[market].index(s["symbol"]))

        return results
    
    def _save_raw_data(self, symbol: str, df: pd.DataFrame):
        """Save raw stock data to CSV."""
        filepath = self._get_raw_filepath(symbol)
        df.to_csv(filepath, index=False)
        logger.info(f"Saved raw data to {filepath} ({len(df)} records)")

    def fetch_macro_indicators(self) -> Dict:
        """Fetch US10Y yield, Dollar Index, VIX, Bitcoin, WTI Crude Oil, and Gold."""
        macro_data = {
            "us10y": {"value": None, "change": None},
            "dxy": {"value": None, "change": None},
            "fear_greed": {"value": None, "label": "N/A"},
            "btc": {"value": None, "change_pct": None},
            "oil": {"value": None, "change": None, "change_pct": None},
            "gold": {"value": None, "change": None, "change_pct": None}
        }

        # 1. Fetch US10Y Yield (^TNX)
        try:
            ticker_us10y = yf.Ticker("^TNX")
            hist_us10y = ticker_us10y.history(period="2d")
            if not hist_us10y.empty:
                latest_val = hist_us10y['Close'].iloc[-1]
                prev_val = hist_us10y['Close'].iloc[-2] if len(hist_us10y) >= 2 else latest_val
                macro_data["us10y"] = {"value": round(latest_val, 3), "change": round(latest_val - prev_val, 3)}
        except Exception as e:
            logger.error(f"Error fetching US10Y: {e}")

        # 2. Fetch Dollar Index (DX-Y.NYB)
        try:
            ticker_dxy = yf.Ticker("DX-Y.NYB")
            hist_dxy = ticker_dxy.history(period="2d")
            if not hist_dxy.empty:
                latest_val = hist_dxy['Close'].iloc[-1]
                prev_val = hist_dxy['Close'].iloc[-2] if len(hist_dxy) >= 2 else latest_val
                macro_data["dxy"] = {"value": round(latest_val, 2), "change": round(latest_val - prev_val, 2)}
        except Exception as e:
            logger.error(f"Error fetching DXY: {e}")

        # 3. Fetch Bitcoin Price (BTC-USD)
        try:
            ticker_btc = yf.Ticker("BTC-USD")
            # Use fast_info for current price as it's more reliable for cryptos
            latest_val = ticker_btc.fast_info.get('lastPrice')
            if latest_val:
                hist_btc = ticker_btc.history(period="2d")
                change_pct = 0
                if len(hist_btc) >= 2:
                    prev_val = hist_btc['Close'].iloc[-2]
                    change_pct = ((latest_val - prev_val) / prev_val) * 100
                macro_data["btc"] = {"value": round(latest_val, 0), "change_pct": round(change_pct, 2)}
            else:
                logger.warning("Could not get Bitcoin price via fast_info")
        except Exception as e:
            logger.error(f"Error fetching BTC: {e}")

        # 4. Fetch VIX Index (^VIX)
        try:
            ticker_vix = yf.Ticker("^VIX")
            hist_vix = ticker_vix.history(period="2d")
            if not hist_vix.empty:
                latest_val = hist_vix['Close'].iloc[-1]
                prev_val = hist_vix['Close'].iloc[-2] if len(hist_vix) >= 2 else latest_val
                macro_data["fear_greed"] = {
                    "value": round(latest_val, 2),
                    "change": round(latest_val - prev_val, 2),
                    "label": "VIX Index",
                    "timestamp": datetime.now().isoformat()
                }
                logger.info(f"VIX Index: {round(latest_val, 2)}")
        except Exception as e:
            logger.error(f"Error fetching VIX: {e}")

        # 5. Fetch WTI Crude Oil futures (CL=F)
        try:
            ticker_oil = yf.Ticker("CL=F")
            hist_oil = ticker_oil.history(period="2d")
            if not hist_oil.empty:
                latest_val = hist_oil['Close'].iloc[-1]
                prev_val = hist_oil['Close'].iloc[-2] if len(hist_oil) >= 2 else latest_val
                change = latest_val - prev_val
                change_pct = (change / prev_val * 100) if prev_val else 0
                macro_data["oil"] = {
                    "value": round(latest_val, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2)
                }
        except Exception as e:
            logger.error(f"Error fetching WTI Crude Oil: {e}")

        # 6. Fetch Gold futures (GC=F)
        try:
            ticker_gold = yf.Ticker("GC=F")
            hist_gold = ticker_gold.history(period="2d")
            if not hist_gold.empty:
                latest_val = hist_gold['Close'].iloc[-1]
                prev_val = hist_gold['Close'].iloc[-2] if len(hist_gold) >= 2 else latest_val
                change = latest_val - prev_val
                change_pct = (change / prev_val * 100) if prev_val else 0
                macro_data["gold"] = {
                    "value": round(latest_val, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2)
                }
        except Exception as e:
            logger.error(f"Error fetching Gold: {e}")

        return macro_data

    def _fetch_twse_latest(self, build_url: Callable[[datetime], str],
                            max_lookback_days: int = 7) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Fetch a TWSE 'rwd' open-data report, walking backward from today until a
        trading day with real data is found.

        TWSE's institutional-investor / margin-trading reports are End-of-Day data:
        they don't exist for weekends/holidays, and the current day's figures aren't
        posted until after market close (roughly 15:00-19:00 Taipei time). Calling
        this before that means today's URL returns an empty/error payload, so we
        fall back to the most recent day that actually has data (up to a week back).

        Returns (parsed_json, "YYYY-MM-DD" of the day the data is actually for), or
        (None, None) if nothing was found in the lookback window.
        """
        headers = {"User-Agent": "Mozilla/5.0 (compatible; KDStockMonitor/1.0)"}
        for offset in range(max_lookback_days):
            day = datetime.now() - timedelta(days=offset)
            url = build_url(day)
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                if data.get("stat") == "OK" and (data.get("data") or data.get("tables")):
                    return data, day.strftime("%Y-%m-%d")
            except Exception as e:
                logger.warning(f"TWSE report fetch failed for {day.strftime('%Y%m%d')} ({url}): {e}")
        return None, None

    @staticmethod
    def _twse_num(raw: str) -> float:
        """Parse a TWSE report cell ('1,234,567' style) into a float."""
        return float(str(raw).replace(",", "").strip() or 0)

    def fetch_tw_chip_indicators(self) -> Dict:
        """
        Fetch Taiwan-market 'chip flow' (籌碼面) indicators from TWSE's free public
        open-data endpoints (no API key required):
          - foreign_net / trust_net: market-wide net buy/sell amount (NT$ 億元) for
            foreign investors and investment trusts, from the daily 三大法人買賣金額
            統計表 (TWSE report BFI82U).
          - margin_balance / short_balance / margin_short_ratio: 融資融券餘額 from
            the daily 信用交易統計 (TWSE report MI_MARGN).
          - usdtwd: USD/TWD exchange rate via yfinance — a coincident/leading signal
            for foreign capital flows into or out of TW equities.

        These are End-of-Day figures, not intraday ticks, so on an hourly refresh
        they'll typically only change once per trading day (when TWSE posts that
        day's numbers in the evening). Each value's 'date' field says which trading
        day it's actually for, so the UI can show that instead of implying it's live.

        Note: this intentionally does NOT include 外資台指期未平倉淨部位 or 選擇權
        Put/Call Ratio (TAIFEX). Those endpoints exist on TAIFEX's official OpenAPI
        but their response schema wasn't verified — adding them blind risked silently
        broken parsing on a production dashboard, so they're left for a follow-up.
        """
        chip_data = {
            "foreign_net": {"value": None, "unit": "億元", "date": None},
            "trust_net": {"value": None, "unit": "億元", "date": None},
            "margin_balance": {"value": None, "change": None, "unit": "張", "date": None},
            "margin_balance_amount": {"value": None, "change": None, "unit": "億元", "date": None},
            "short_balance": {"value": None, "change": None, "unit": "張", "date": None},
            "margin_short_ratio": {"value": None, "unit": "%"},
            "usdtwd": {"value": None, "change": None}
        }

        # 1+2. 三大法人買賣金額統計表 (foreign + investment trust net buy/sell, NT$)
        try:
            data, report_date = self._fetch_twse_latest(
                lambda d: f"https://www.twse.com.tw/rwd/zh/fund/BFI82U?dayDate={d.strftime('%Y%m%d')}&type=day&response=json"
            )
            if data:
                rows = {row[0]: row for row in data.get("data", [])}
                foreign_row = rows.get("外資及陸資(不含外資自營商)")
                trust_row = rows.get("投信")
                if foreign_row:
                    net = self._twse_num(foreign_row[3]) / 1e8  # NT$ -> 億元
                    chip_data["foreign_net"] = {"value": round(net, 2), "unit": "億元", "date": report_date}
                if trust_row:
                    net = self._twse_num(trust_row[3]) / 1e8
                    chip_data["trust_net"] = {"value": round(net, 2), "unit": "億元", "date": report_date}
        except Exception as e:
            logger.error(f"Error fetching TWSE BFI82U (三大法人買賣金額): {e}")

        # 3+4+5. 融資融券餘額 (margin / short balance + 資券比)
        try:
            data, report_date = self._fetch_twse_latest(
                lambda d: f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date={d.strftime('%Y%m%d')}&response=json&selectType=ALL"
            )
            if data and data.get("tables"):
                summary_table = data["tables"][0]  # 信用交易統計 (market-wide aggregate)
                rows = {row[0]: row for row in summary_table.get("data", [])}
                # fields: [項目, 買進, 賣出, 現金(券)償還, 前日餘額, 今日餘額]
                margin_row = rows.get("融資(交易單位)")
                margin_amount_row = rows.get("融資金額(仟元)")
                short_row = rows.get("融券(交易單位)")

                margin_today = None
                short_today = None
                if margin_row:
                    margin_today = self._twse_num(margin_row[5])
                    margin_prev = self._twse_num(margin_row[4])
                    chip_data["margin_balance"] = {
                        "value": margin_today, "change": round(margin_today - margin_prev, 0),
                        "unit": "張", "date": report_date
                    }
                if margin_amount_row:
                    # 仟元 (thousands of NT$) -> 億元 (hundred-millions), matches how
                    # 融資斷頭 is usually reported in the news ("單日減幅數十億")
                    amount_today = self._twse_num(margin_amount_row[5]) * 1000 / 1e8
                    amount_prev = self._twse_num(margin_amount_row[4]) * 1000 / 1e8
                    chip_data["margin_balance_amount"] = {
                        "value": round(amount_today, 2), "change": round(amount_today - amount_prev, 2),
                        "unit": "億元", "date": report_date
                    }
                if short_row:
                    short_today = self._twse_num(short_row[5])
                    short_prev = self._twse_num(short_row[4])
                    chip_data["short_balance"] = {
                        "value": short_today, "change": round(short_today - short_prev, 0),
                        "unit": "張", "date": report_date
                    }
                if margin_today and short_today is not None:
                    chip_data["margin_short_ratio"] = {
                        "value": round(short_today / margin_today * 100, 2), "unit": "%"
                    }
        except Exception as e:
            logger.error(f"Error fetching TWSE MI_MARGN (融資融券): {e}")

        # 6. USD/TWD exchange rate
        try:
            ticker_twd = yf.Ticker("TWD=X")
            hist_twd = ticker_twd.history(period="5d")
            if not hist_twd.empty:
                latest_val = hist_twd['Close'].iloc[-1]
                prev_val = hist_twd['Close'].iloc[-2] if len(hist_twd) >= 2 else latest_val
                chip_data["usdtwd"] = {"value": round(latest_val, 3), "change": round(latest_val - prev_val, 3)}
        except Exception as e:
            logger.error(f"Error fetching USD/TWD: {e}")

        return chip_data
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get the latest closing price for a stock."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Try currentPrice first, then regularMarketPrice
            price = info.get('currentPrice') or info.get('regularMarketPrice')
            if price:
                return float(price)
            
            # Fallback to historical data
            df = self.fetch_stock_data(symbol, period="5d")
            if df is not None and not df.empty:
                return float(df['close'].iloc[-1])
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest price for {symbol}: {e}")
            return None
    
    def get_stock_info(self, symbol: str) -> Dict:
        """Get stock information from Yahoo Finance."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                "symbol": symbol,
                "name": info.get('longName') or info.get('shortName', symbol),
                "sector": info.get('sector', 'N/A'),
                "industry": info.get('industry', 'N/A'),
                "market_cap": info.get('marketCap'),
                "currency": info.get('currency', 'USD'),
                "website": info.get('website', '')
            }
        except Exception as e:
            logger.error(f"Error getting info for {symbol}: {e}")
            return {"symbol": symbol, "name": symbol}


def main():
    """Test the fetcher."""
    fetcher = StockFetcher()
    
    # Test single stock
    df = fetcher.fetch_stock_data("AAPL", period="1mo")
    if df is not None:
        print(f"\nSample data for AAPL:")
        print(df.tail())
        print(f"\nLatest price: {fetcher.get_latest_price('AAPL')}")
    
    # Test fetching all stocks
    print("\n" + "="*50)
    print("Fetching all configured stocks...")
    all_data = fetcher.fetch_all_stocks()
    
    for market, stocks in all_data.items():
        print(f"\n{market} Stocks fetched: {len(stocks)}")
        for stock in stocks:
            print(f"  - {stock['symbol']}: {len(stock['data'])} records")


if __name__ == "__main__":
    main()
