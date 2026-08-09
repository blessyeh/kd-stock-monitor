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

        Initialization convention (stated explicitly here since it's a real
        design choice, not an incidental detail — other TA libraries make a
        different choice and will disagree with this one for the first
        k_period-1 rows of any given series):
          - Rows 0 .. k_period-2 (fewer than k_period days of range data
            available) get K=D=50.0 flat, rather than participating in the
            recursive formula early with a partial/skewed lookback window.
            This avoids a misleadingly precise-looking KD reading before
            there's actually a full window to compute RSV's range from.
          - The recursive formula starts at row k_period-1, seeded from
            prev_k=prev_d=50.0 (the same neutral value, not the row's own
            RSV) — this is the standard "seed at 50" convention, distinct
            from libraries that seed K/D = RSV on the very first row and
            recurse from there. Expect a several-day "settling in" period
            before K/D converge to the same values a chart platform seeded
            differently would show.
        """
        result_df = df.copy()

        # Calculate lowest low and highest high over k_period
        low_min = result_df['low'].rolling(window=k_period, min_periods=1).min()
        high_max = result_df['high'].rolling(window=k_period, min_periods=1).max()

        # RSV (Raw Stochastic Value). A flat range (high_max == low_min, e.g.
        # a halted/illiquid stock trading in a single tick all day, or the
        # very first row where high==low==close) is a genuine, well-defined
        # case — RSV is neutral (50) there *by definition*, not because data
        # is missing. Previously this was handled with a single
        # `rsv.fillna(50)` after a division that produces NaN/inf on a
        # zero-width range, which happened to land on the same 50 value but
        # conflated "range is genuinely flat" with "this row is otherwise
        # broken" (e.g. a future bug that produces NaN for an unrelated
        # reason would silently get the same neutral treatment). Made
        # explicit here: default every row to 50, then only overwrite the
        # rows where the range is actually non-zero with the real computed
        # RSV — anything that stays at the 50 default did so because of the
        # flat-range case specifically, not through fillna() catching an
        # unknown NaN source.
        price_range = high_max - low_min
        has_range = price_range > 0
        rsv = pd.Series(50.0, index=result_df.index)
        rsv.loc[has_range] = (
            100 * (result_df.loc[has_range, 'close'] - low_min.loc[has_range]) / price_range.loc[has_range]
        )

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

                        # KD state (see analyze_kd_signal's docstring) — needs
                        # yesterday's K/D too, for crossover/momentum detection.
                        kd_k_prev = kd_d_prev = None
                        if len(df_with_kd) >= 2:
                            prev_row = df_with_kd.iloc[-2]
                            kd_k_prev = float(prev_row['kd_k']) if pd.notna(prev_row.get('kd_k')) else None
                            kd_d_prev = float(prev_row['kd_d']) if pd.notna(prev_row.get('kd_d')) else None
                        kd_state = None
                        if current_kd and current_kd.get("kd_k") is not None and current_kd.get("kd_d") is not None:
                            kd_state = self.analyze_kd_signal(
                                current_kd["kd_k"], current_kd["kd_d"], kd_k_prev, kd_d_prev
                            )

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
                            "kd_state": kd_state,
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
    
    def analyze_kd_signal(self, kd_k: float, kd_d: float,
                           kd_k_prev: Optional[float] = None, kd_d_prev: Optional[float] = None) -> str:
        """
        Classify today's KD reading into one of 10 states, rather than the
        coarse overbought/oversold/bullish/bearish/neutral this function
        previously returned.

        Why this changed: a bare "K>=80 and D>=80 -> overbought" treats
        K=95/D=80 (gap wide and, if K is still climbing, widening — momentum
        still building) the same as K=95/D=94 (gap almost closed — momentum
        stalling, a down-cross is close). Those are different market states
        with different implications, and the old version couldn't tell them
        apart. This version also fixes a real docstring/implementation
        mismatch: the previous docstring promised 'golden_cross'/'death_cross'
        as possible return values, but the function never actually computed
        or returned either — there was no crossover detection at all.

        Pass kd_k_prev/kd_d_prev (yesterday's K/D — calculate_all_stocks()
        supplies these from history) to enable crossover and momentum
        (rising/falling, gap widening/narrowing) detection. Without them,
        this falls back to a zone-only classification (OVERBOUGHT / OVERSOLD
        / BULLISH_MOMENTUM / BEARISH_MOMENTUM / NEUTRAL) — still useful, just
        less specific.

        Returns one of:
            GOLDEN_CROSS         — K crossed above D today (either zone)
            DEATH_CROSS          — K crossed below D today (either zone)
            OVERBOUGHT_BUT_RISING — in overbought zone, K-D gap still widening
                                     (or K still rising) — momentum intact, a
                                     raw KD>=80 sell alert here is more likely
                                     鈍化 (indicator stuck) than a real top
            OVERBOUGHT_REVERSAL  — in overbought zone, gap narrowing / K
                                     falling — momentum stalling, more likely
                                     a genuine top forming
            OVERBOUGHT           — in overbought zone, not enough prior data
                                     to tell the two apart
            OVERSOLD_REVERSAL    — in oversold zone, K rising and gap
                                     narrowing (climbing back toward D) — the
                                     clearest pre-golden-cross bottoming signal
            OVERSOLD_BUT_RISING  — in oversold zone, K rising but gap not yet
                                     meaningfully narrowing — early/unconfirmed
            OVERSOLD              — in oversold zone, not enough prior data
                                     (or still falling) to call it a reversal
            BULLISH_MOMENTUM     — K > D, outside both extreme zones
            BEARISH_MOMENTUM     — K < D, outside both extreme zones
            NEUTRAL               — K == D, or insufficient input
        """
        if kd_k is None or kd_d is None:
            return "NEUTRAL"

        thresholds = self.config.get("alert_thresholds", {"overbought": 80, "oversold": 20})
        overbought = thresholds.get("overbought", 80)
        oversold = thresholds.get("oversold", 20)

        have_prev = kd_k_prev is not None and kd_d_prev is not None
        gap = kd_k - kd_d
        gap_prev = (kd_k_prev - kd_d_prev) if have_prev else None
        k_rising = have_prev and kd_k > kd_k_prev
        k_falling = have_prev and kd_k < kd_k_prev
        # "Widening" / "narrowing" compares magnitude, not signed value, so it
        # means the same thing (momentum strengthening vs. stalling) whether
        # gap is positive (K above D) or negative (K below D).
        gap_widening = gap_prev is not None and abs(gap) > abs(gap_prev)
        gap_narrowing = gap_prev is not None and abs(gap) < abs(gap_prev)

        crossed_up = have_prev and kd_k_prev <= kd_d_prev and kd_k > kd_d
        crossed_down = have_prev and kd_k_prev >= kd_d_prev and kd_k < kd_d

        if crossed_up:
            return "GOLDEN_CROSS"
        if crossed_down:
            return "DEATH_CROSS"

        if kd_k >= overbought and kd_d >= overbought:
            if gap_widening or (k_rising and not gap_narrowing):
                return "OVERBOUGHT_BUT_RISING"
            if gap_narrowing or k_falling:
                return "OVERBOUGHT_REVERSAL"
            return "OVERBOUGHT"

        if kd_k <= oversold and kd_d <= oversold:
            if k_rising and gap_narrowing:
                return "OVERSOLD_REVERSAL"
            if k_rising:
                return "OVERSOLD_BUT_RISING"
            return "OVERSOLD"

        if kd_k > kd_d:
            return "BULLISH_MOMENTUM"
        if kd_k < kd_d:
            return "BEARISH_MOMENTUM"
        return "NEUTRAL"


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