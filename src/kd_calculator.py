#!/usr/bin/env python3
"""
KD Calculator - Calculates Stochastic Oscillator (KD) indicator using pandas_ta.
"""

import pandas as pd
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class KDCalculator:
    """Calculates KD (Stochastic Oscillator) indicator for stock data."""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize with configuration."""
        self.config = self._load_config(config_path)
        self.kd_settings = self.config.get("kd_settings", {"k_period": 9})
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file."""
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def calculate_kd(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate KD (Stochastic Oscillator) for the given DataFrame.
        Drops rows with NaN in required price columns before calculation.
        """
        if df is None or df.empty:
            raise ValueError("DataFrame is empty or None")
        
        required_cols = ['high', 'low', 'close']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Required column '{col}' not found in DataFrame")
        
        # Drop rows with NaN in price columns to prevent KD contamination
        result_df = df.dropna(subset=required_cols).copy()
        if len(result_df) < len(df):
            logger.warning(f"Dropped {len(df) - len(result_df)} rows with NaN prices before KD calculation")
        
        if result_df.empty:
            raise ValueError("No valid price data after dropping NaN rows")
        
        # Get settings
        k_period = self.kd_settings.get("k_period", 9)

        # Calculate KD using manual method
        result_df = self._calculate_kd_manual(result_df, k_period)

        return result_df

    def _calculate_kd_manual(self, df: pd.DataFrame, k_period: int) -> pd.DataFrame:
        """
        Manual KD calculation (Taiwan style).

        RSV = 100 * (Close - Lowest Low) / (Highest High - Lowest Low)
        K = (2/3) * Previous K + (1/3) * RSV
        D = (2/3) * Previous D + (1/3) * K

        Note: the 2/3 and 1/3 smoothing weights are fixed by convention for the
        standard Taiwan-style KD formula and are NOT derived from a separate
        "d_period"/"smooth" setting — only the RSV lookback window (k_period,
        default 9 days) is configurable. Earlier versions of config.json exposed
        unused d_period/smooth keys that had no effect on this calculation; they
        were removed to avoid the false impression that changing them does anything.
        """
        result_df = df.copy()
        
        # Calculate lowest low and highest high over k_period
        low_min = result_df['low'].rolling(window=k_period, min_periods=1).min()
        high_max = result_df['high'].rolling(window=k_period, min_periods=1).max()
        
        # Calculate RSV (Raw Stochastic Value)
        rsv = 100 * (result_df['close'] - low_min) / (high_max - low_min)
        rsv = rsv.fillna(50)  # Fill NaN with neutral value
        
        # Initialize K and D arrays
        k_values = []
        d_values = []
        prev_k = 50.0  # Initial value
        prev_d = 50.0  # Initial value
        
        for i, rsv_val in enumerate(rsv):
            if i < k_period - 1:
                # Not enough data yet, use neutral values
                k_values.append(50.0)
                d_values.append(50.0)
            else:
                # Calculate K and D
                k = (2/3) * prev_k + (1/3) * rsv_val
                d = (2/3) * prev_d + (1/3) * k
                k_values.append(k)
                d_values.append(d)
                prev_k = k
                prev_d = d
        
        result_df['kd_k'] = pd.Series(k_values, index=result_df.index).round(2)
        result_df['kd_d'] = pd.Series(d_values, index=result_df.index).round(2)
        
        logger.info("KD calculated using Taiwan style formula")
        return result_df
    
    def calculate_bias(self, df: pd.DataFrame, period: int) -> pd.Series:
        """
        Calculate Bias (乖離率) for the given DataFrame.
        
        Bias = (Close - MA) / MA * 100%
        """
        if df is None or df.empty or 'close' not in df.columns:
            return pd.Series()
        
        ma = df['close'].rolling(window=period, min_periods=1).mean()
        bias = (df['close'] - ma) / ma * 100
        return bias.round(2)
    
    def get_current_bias(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Get the most recent BIAS values from a DataFrame.
        
        Returns:
            Dictionary with current bias_5, bias_10, bias_20 values, or None
        """
        if df is None or df.empty:
            return None
        
        result = {}
        for period in [5, 10, 20]:
            col = f'bias_{period}'
            if col in df.columns:
                latest = df[col].iloc[-1]
                result[col] = float(latest) if pd.notna(latest) else None
            else:
                result[col] = None
        
        return result if result else None
    
    def get_current_kd(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Get the most recent KD values from a DataFrame.
        
        Returns:
            Dictionary with current K, D values and date, or None if not available
        """
        if df is None or df.empty:
            return None
        
        if 'kd_k' not in df.columns or 'kd_d' not in df.columns:
            return None
        
        latest = df.iloc[-1]
        
        return {
            "kd_k": float(latest['kd_k']) if pd.notna(latest['kd_k']) else None,
            "kd_d": float(latest['kd_d']) if pd.notna(latest['kd_d']) else None,
            "date": str(latest.get('date', latest.name)) if isinstance(latest.name, pd.Timestamp) else str(df.index[-1]),
            "close": float(latest['close']) if 'close' in latest else None
        }
    
    def calculate_all_stocks(self, stock_data: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """
        Calculate KD for all stocks in the provided data.
        
        Args:
            stock_data: Dictionary with 'TW' and 'US' keys containing stock data
        
        Returns:
            Dictionary with KD values added to each stock
        """
        results = {"TW": [], "US": []}
        
        for market in ["TW", "US"]:
            for stock in stock_data.get(market, []):
                symbol = stock["symbol"]
                df = stock.get("data")
                
                if df is not None and not df.empty:
                    try:
                        # Calculate KD
                        df_with_kd = self.calculate_kd(df)
                        current_kd = self.get_current_kd(df_with_kd)
                        
                        # Calculate BIAS (乖離率)
                        for period in [5, 10, 20]:
                            df_with_kd[f'bias_{period}'] = self.calculate_bias(df_with_kd, period)
                        current_bias = self.get_current_bias(df_with_kd)
                        
                        # Calculate daily change percentage
                        extra_data = stock.get("extra_data", {})
                        change_pct = 0.0
                        
                        reg_price = extra_data.get("regular_market_price")
                        prev_close = extra_data.get("prev_close")
                        
                        if reg_price is not None and prev_close is not None:
                            change_pct = ((reg_price - prev_close) / prev_close) * 100
                            logger.info(f"Calculated change_pct for {symbol} using real-time info: {change_pct:.2f}%")
                        elif len(df_with_kd) >= 2:
                            current_close = df_with_kd['close'].iloc[-1]
                            hist_prev_close = df_with_kd['close'].iloc[-2]
                            change_pct = ((current_close - hist_prev_close) / hist_prev_close) * 100
                            logger.info(f"Calculated change_pct for {symbol} using history: {change_pct:.2f}%")
                        
                        # Save processed data
                        self._save_processed_data(symbol, df_with_kd)
                        
                        # Build history columns
                        hist_cols = ['date', 'open', 'high', 'low', 'close', 'volume', 'kd_k', 'kd_d']
                        for p in [5, 10, 20]:
                            if f'bias_{p}' in df_with_kd.columns:
                                hist_cols.append(f'bias_{p}')
                        
                        results[market].append({
                            "symbol": symbol,
                            "name": stock["name"],
                            "market": market,
                            "current_price": reg_price if reg_price is not None else (current_kd.get("close") if current_kd else None),
                            "change_pct": round(change_pct, 2),
                            "extra_data": extra_data,
                            "kd_k": current_kd.get("kd_k") if current_kd else None,
                            "kd_d": current_kd.get("kd_d") if current_kd else None,
                            "bias_5": current_bias.get("bias_5") if current_bias else None,
                            "bias_10": current_bias.get("bias_10") if current_bias else None,
                            "bias_20": current_bias.get("bias_20") if current_bias else None,
                            "last_updated": stock.get("last_updated"),
                            "data_points": len(df_with_kd),
                            "history": df_with_kd[hist_cols].to_dict('records')[-500:]  # Last 500 days
                        })
                        
                        logger.info(f"KD calculated for {symbol}: K={current_kd.get('kd_k')}, D={current_kd.get('kd_d')}, BIAS5={current_bias.get('bias_5') if current_bias else None}")
                        
                    except Exception as e:
                        logger.error(f"Error calculating KD for {symbol}: {e}")
                        results[market].append({
                            "symbol": symbol,
                            "name": stock["name"],
                            "market": market,
                            "error": str(e)
                        })
        
        return results
    
    def _save_processed_data(self, symbol: str, df: pd.DataFrame):
        """Save processed data with KD values to CSV."""
        filepath = os.path.join(self.data_dir, f"{symbol.replace('.', '_')}_kd.csv")
        df.to_csv(filepath, index=False)
        logger.info(f"Saved processed data to {filepath}")
    
    def analyze_kd_signal(self, kd_k: float, kd_d: float) -> str:
        """
        Analyze KD values and return a signal description.
        
        Returns:
            Signal description: 'overbought', 'oversold', 'golden_cross', 'death_cross', or 'neutral'
        """
        thresholds = self.config.get("alert_thresholds", {"overbought": 80, "oversold": 20})
        overbought = thresholds.get("overbought", 80)
        oversold = thresholds.get("oversold", 20)
        
        if kd_k >= overbought and kd_d >= overbought:
            return "overbought"
        elif kd_k <= oversold and kd_d <= oversold:
            return "oversold"
        elif kd_k > kd_d:
            return "bullish"  # K above D is generally bullish
        elif kd_k < kd_d:
            return "bearish"  # K below D is generally bearish
        else:
            return "neutral"


def main():
    """Test the KD calculator."""
    from fetcher import StockFetcher
    
    # Fetch some test data
    fetcher = StockFetcher()
    df = fetcher.fetch_stock_data("AAPL", period="1mo")
    
    if df is not None:
        calculator = KDCalculator()
        
        # Calculate KD
        df_with_kd = calculator.calculate_kd(df)
        
        print("\nLast 5 days with KD values:")
        print(df_with_kd[['date', 'close', 'kd_k', 'kd_d']].tail())
        
        # Get current KD
        current = calculator.get_current_kd(df_with_kd)
        print(f"\nCurrent KD values:")
        print(f"  K: {current['kd_k']}")
        print(f"  D: {current['kd_d']}")
        print(f"  Signal: {calculator.analyze_kd_signal(current['kd_k'], current['kd_d'])}")


if __name__ == "__main__":
    main()