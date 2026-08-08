#!/usr/bin/env python3
"""
Alert Checker - Checks if KD >= 80 or <= 20 and generates alerts.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

# Import pattern analyzer
try:
    from pattern_analyzer import analyze_stock_patterns
    PATTERN_ANALYSIS_AVAILABLE = True
except ImportError:
    PATTERN_ANALYSIS_AVAILABLE = False
    logging.warning("Pattern analyzer not available")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AlertChecker:
    """Checks KD values and generates alerts for overbought/oversold conditions."""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize with configuration."""
        self.config = self._load_config(config_path)
        self.thresholds = self.config.get("alert_thresholds", {
            "overbought": 80,
            "oversold": 20
        })
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        self.alerts_file = os.path.join(self.data_dir, 'alerts.json')
        self.stock_data_file = os.path.join(self.data_dir, 'stock_data.json')
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file."""
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_existing_alerts(self) -> List[Dict]:
        """Load existing alerts from file."""
        if os.path.exists(self.alerts_file):
            try:
                with open(self.alerts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading alerts: {e}")
                return []
        return []
    
    def _save_alerts(self, alerts: List[Dict]):
        """Save alerts to file."""
        try:
            with open(self.alerts_file, 'w', encoding='utf-8') as f:
                json.dump(alerts, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(alerts)} alerts to {self.alerts_file}")
        except Exception as e:
            logger.error(f"Error saving alerts: {e}")
    
    def _evaluate_filters(self, stock_data: Dict, direction: str) -> Dict:
        """
        Multi-filter confirmation for a raw KD extreme reading.

        KD is a bounded oscillator: it assumes price mean-reverts inside a
        range, so it "sticks" (鈍化 / indicator failure) at the extremes
        during a strong trend — a KD<=20 reading can persist for weeks in a
        real downtrend (there's no bottom to catch), and a KD>=80 reading can
        persist for weeks in a strong uptrend (selling early misses the
        whole rally). A bare `if kd_k <= 20` alert can't tell the difference
        between "oversold bounce coming" and "downtrend, keep falling".

        This runs the raw KD reading through the trend/volume/MACD/Bollinger
        data already computed by ScoringEngine (main.py's Step 2.5, before
        alerts are checked) to flag which of those two situations it more
        likely is — without hiding the raw KD reading itself. Every KD
        extreme still produces an alert; this only adds a confidence tag and
        the concrete reasons behind it, mirroring how signal_confluence.py
        already reports per-condition completeness rather than a bare bool.

        Returns:
            {
                "available": bool — whether enough history existed to run the filters,
                "confirmed": bool — filters agree with the raw KD signal,
                "passed": [str, ...] — filter checks that support the KD signal,
                "cautions": [str, ...] — filter checks that argue against it,
            }
        """
        score = stock_data.get("score") or {}
        raw = score.get("raw") or {}
        price = stock_data.get("current_price")

        ma20 = raw.get("ma20")
        macd_hist = raw.get("macd_hist")
        macd_hist_prev = raw.get("macd_hist_prev")
        volume_ratio = raw.get("volume_ratio")
        bb_upper = raw.get("bb_upper")
        bb_lower = raw.get("bb_lower")

        # "MA20 上彎" is checked directly against MA20's own value 5 trading
        # days ago, rather than reusing ScoringEngine's `trend_dir` (a 20-day
        # linear-regression slope categorized into up/down/flat with a
        # deliberately strict >1% threshold, tuned for the scoring/
        # recommendation dimension — not a plain "is the average rising"
        # check). Using MA20-vs-5-days-ago keeps this filter matching the
        # everyday reading of "均線上彎" instead of only firing in unusually
        # steep trends.
        closes = [h.get("close") for h in (stock_data.get("history") or []) if h.get("close") is not None]
        ma20_prev = sum(closes[-25:-5]) / 20 if len(closes) >= 25 else None

        available = price is not None and ma20 is not None and ma20_prev is not None
        if not available:
            return {"available": False, "confirmed": True, "passed": [], "cautions": []}

        above_ma20 = price > ma20
        ma20_rising = ma20 > ma20_prev
        bullish_regime = above_ma20 and ma20_rising

        macd_diverging_down = (
            macd_hist is not None and macd_hist_prev is not None
            and macd_hist < 0 and macd_hist < macd_hist_prev
        )
        macd_diverging_up = (
            macd_hist is not None and macd_hist_prev is not None
            and macd_hist > 0 and macd_hist > macd_hist_prev
        )
        volume_confirmed = volume_ratio is not None and volume_ratio > 1.0

        # Per-stock 外資買賣超 (individual-holding foreign flow, from
        # fetch_stock_institutional_flow — not the market-wide foreign_net
        # already covered in signal_confluence.py). Uses the 3-day cumulative
        # net rather than a single day to cut down single-day noise; a small
        # threshold (500 張 = 500,000 股) avoids treating negligible flow as a
        # meaningful signal either way.
        institutional = stock_data.get("institutional") or {}
        foreign_net_3d = institutional.get("foreign_net_3d")
        foreign_buying = foreign_net_3d is not None and foreign_net_3d > 500_000
        foreign_selling = foreign_net_3d is not None and foreign_net_3d < -500_000

        passed, cautions = [], []

        if direction == "oversold":
            bollinger_touch = bb_lower is not None and price <= bb_lower * 1.01
            if bullish_regime:
                passed.append("股價站上上彎的20日均線之上（回檔至低檔，非空頭趨勢中的破底）")
            else:
                cautions.append("股價在20日均線之下或均線走平/下彎（可能處於空頭趨勢，KD超賣可能鈍化、續跌機率較高）")
            if bollinger_touch:
                passed.append("股價觸及/跌破布林通道下軌（統計上短線反彈機率較高）")
            if macd_diverging_down:
                cautions.append("MACD柱狀體在零軸下持續擴大（空頭動能未歇，不宜視為買進訊號）")
            if foreign_buying:
                passed.append(f"個股外資近3日同步買超 {foreign_net_3d/1000:.0f} 張（籌碼面轉強，非籌碼出走）")
            elif foreign_selling:
                cautions.append(f"個股外資近3日仍賣超 {abs(foreign_net_3d)/1000:.0f} 張（籌碼仍在流出，KD超賣可能持續鈍化）")
            confirmed = (bullish_regime or bollinger_touch or foreign_buying) and not macd_diverging_down
        else:  # overbought
            bollinger_touch = bb_upper is not None and price >= bb_upper * 0.99
            if bullish_regime:
                cautions.append("股價仍在上彎的20日均線之上（強勢多頭排列，KD高檔鈍化風險高，未必是賣出訊號）")
            else:
                passed.append("股價未站穩上彎的20日均線之上（超買對應轉弱的可能性較高）")
            if bollinger_touch and not volume_confirmed:
                passed.append("股價觸及布林通道上軌但成交量未放大（追高動能不足，短線過熱風險較高）")
            if macd_diverging_up:
                cautions.append("MACD柱狀體在零軸上持續擴大（多頭動能仍強，超買可能只是鈍化）")
            if foreign_selling:
                passed.append(f"個股外資近3日轉為賣超 {abs(foreign_net_3d)/1000:.0f} 張（籌碼面轉弱，超買可能對應真正高點）")
            elif foreign_buying:
                cautions.append(f"個股外資近3日仍買超 {foreign_net_3d/1000:.0f} 張（籌碼面仍強，超買可能只是鈍化）")
            confirmed = (not bullish_regime) or (bollinger_touch and not volume_confirmed) or foreign_selling

        return {"available": True, "confirmed": confirmed, "passed": passed, "cautions": cautions}

    def check_stock(self, stock_data: Dict) -> Optional[Dict]:
        """
        Check a single stock for KD alert conditions.

        Args:
            stock_data: Dictionary containing stock info with kd_k and kd_d values

        Returns:
            Alert dictionary if condition met, None otherwise
        """
        symbol = stock_data.get("symbol")
        kd_k = stock_data.get("kd_k")
        kd_d = stock_data.get("kd_d")
        current_price = stock_data.get("current_price")

        if kd_k is None or kd_d is None:
            logger.warning(f"Missing KD values for {symbol}")
            return None

        overbought_threshold = self.thresholds.get("overbought", 80)
        oversold_threshold = self.thresholds.get("oversold", 20)

        alert = None

        # Check overbought condition (KD >= 80)
        if kd_k >= overbought_threshold or kd_d >= overbought_threshold:
            f = self._evaluate_filters(stock_data, "overbought")
            confidence = "unknown" if not f["available"] else ("high" if f["confirmed"] else "low")
            suffix = ""
            if f["available"] and not f["confirmed"]:
                suffix = "（⚠️ 疑似高檔鈍化，非明確賣出訊號）"
            alert = {
                "id": f"{symbol}_{datetime.now().strftime('%Y%m%d')}_overbought",
                "symbol": symbol,
                "name": stock_data.get("name", symbol),
                "market": stock_data.get("market", "UNKNOWN"),
                "type": "overbought",
                "level": "high",
                "kd_k": kd_k,
                "kd_d": kd_d,
                "current_price": current_price,
                "threshold": overbought_threshold,
                "filter_confidence": confidence,
                "filter_passed": f["passed"],
                "filter_cautions": f["cautions"],
                "message": f"⚠️ {symbol} ({stock_data.get('name', symbol)}) is OVERBOUGHT! KD-K: {kd_k}, KD-D: {kd_d} (>= {overbought_threshold}){suffix}",
                "timestamp": datetime.now().isoformat(),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "acknowledged": False
            }
            logger.warning(f"ALERT: {symbol} is overbought! K={kd_k}, D={kd_d}, confidence={confidence}")

        # Check oversold condition (KD <= 20)
        elif kd_k <= oversold_threshold or kd_d <= oversold_threshold:
            f = self._evaluate_filters(stock_data, "oversold")
            confidence = "unknown" if not f["available"] else ("high" if f["confirmed"] else "low")
            suffix = ""
            if f["available"] and not f["confirmed"]:
                suffix = "（⚠️ 疑似低檔鈍化/空頭趨勢，非明確買進訊號）"
            alert = {
                "id": f"{symbol}_{datetime.now().strftime('%Y%m%d')}_oversold",
                "symbol": symbol,
                "name": stock_data.get("name", symbol),
                "market": stock_data.get("market", "UNKNOWN"),
                "type": "oversold",
                "level": "low",
                "kd_k": kd_k,
                "kd_d": kd_d,
                "current_price": current_price,
                "threshold": oversold_threshold,
                "filter_confidence": confidence,
                "filter_passed": f["passed"],
                "filter_cautions": f["cautions"],
                "message": f"✅ {symbol} ({stock_data.get('name', symbol)}) is OVERSOLD! KD-K: {kd_k}, KD-D: {kd_d} (<= {oversold_threshold}){suffix}",
                "timestamp": datetime.now().isoformat(),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "acknowledged": False
            }
            logger.info(f"ALERT: {symbol} is oversold! K={kd_k}, D={kd_d}, confidence={confidence}")

        return alert
    
    def check_all_stocks(self, stocks_data: Dict[str, List[Dict]]) -> List[Dict]:
        """
        Check all stocks for alert conditions.
        
        Args:
            stocks_data: Dictionary with 'TW' and 'US' keys containing stock data
        
        Returns:
            List of alert dictionaries
        """
        new_alerts = []
        
        for market in ["TW", "US"]:
            for stock in stocks_data.get(market, []):
                alert = self.check_stock(stock)
                if alert:
                    new_alerts.append(alert)
        
        return new_alerts
    
    def process_alerts(self, stocks_data: Dict[str, List[Dict]]) -> Dict:
        """
        Process all stocks and update alerts.
        
        Returns:
            Dictionary with alert summary and all current alerts
        """
        # Load existing alerts
        existing_alerts = self._load_existing_alerts()
        
        # Check for new alerts
        new_alerts = self.check_all_stocks(stocks_data)
        
        # Filter out duplicate alerts for the same symbol on the same day
        existing_ids = {alert["id"] for alert in existing_alerts}
        unique_new_alerts = [alert for alert in new_alerts if alert["id"] not in existing_ids]
        
        # Combine alerts (newest first)
        all_alerts = unique_new_alerts + existing_alerts
        
        # Limit to last 100 alerts to prevent file bloat
        all_alerts = all_alerts[:100]
        
        # Save updated alerts
        self._save_alerts(all_alerts)
        
        # Save stock data for dashboard
        self._save_stock_data(stocks_data)
        
        # Generate summary
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_stocks_checked": sum(len(stocks_data.get(m, [])) for m in ["TW", "US"]),
            "new_alerts": len(unique_new_alerts),
            "total_alerts": len(all_alerts),
            "overbought_alerts": len([a for a in unique_new_alerts if a["type"] == "overbought"]),
            "oversold_alerts": len([a for a in unique_new_alerts if a["type"] == "oversold"]),
            "active_alerts": len([a for a in all_alerts if not a.get("acknowledged", False)])
        }
        
        logger.info(f"Alert processing complete: {summary}")
        
        return {
            "summary": summary,
            "new_alerts": unique_new_alerts,
            "all_alerts": all_alerts
        }
    
    def _serialize_score(self, score: Optional[Dict]) -> Optional[Dict]:
        """Serialize score dict, converting numpy types to native Python types."""
        if score is None:
            return None
        import json
        # Round-trip through JSON to convert numpy types
        try:
            return json.loads(json.dumps(score, default=lambda x: float(x) if hasattr(x, '__float__') else str(x)))
        except Exception:
            return None
    
    def _analyze_stock_pattern(self, stock_data: Dict) -> Dict:
        """Analyze trading patterns for a single stock."""
        if not PATTERN_ANALYSIS_AVAILABLE:
            return {
                "patterns_detected": 0,
                "patterns": [],
                "dominant_signal": "HOLD",
                "signal_strength": 0
            }
        
        try:
            # Import pandas here to avoid dependency issues
            import pandas as pd
            
            # Reconstruct DataFrame from history
            history = stock_data.get("history", [])
            if len(history) < 30:
                return {
                    "patterns_detected": 0,
                    "patterns": [],
                    "dominant_signal": "HOLD",
                    "signal_strength": 0,
                    "note": "Insufficient data (need 30 days)"
                }
            
            # Create DataFrame
            df = pd.DataFrame(history)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            # Rename columns to match expected format
            df.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            }, inplace=True)
            
            # Analyze patterns
            return analyze_stock_patterns(df)
            
        except Exception as e:
            logger.error(f"Error analyzing patterns for {stock_data.get('symbol')}: {e}")
            return {
                "patterns_detected": 0,
                "patterns": [],
                "dominant_signal": "HOLD",
                "signal_strength": 0,
                "error": str(e)
            }
    
    def _save_stock_data(self, stocks_data: Dict[str, List[Dict]]):
        """Save processed stock data for dashboard use."""
        try:
            # Prepare data for dashboard (remove large history arrays)
            dashboard_data = {"TW": [], "US": [], "last_updated": datetime.now().isoformat()}
            
            for market in ["TW", "US"]:
                for stock in stocks_data.get(market, []):
                    # Convert history dates to strings to ensure JSON serialization
                    # Keep only last 15 records for sparkline charts (frontend uses slice(-10))
                    history = stock.get("history", [])[-15:] if "history" in stock else []
                    clean_history = []
                    for h in history:
                        # Skip records with NaN values (JavaScript JSON.parse cannot handle NaN)
                        has_nan = False
                        for key in ['open', 'high', 'low', 'close', 'volume', 'kd_k', 'kd_d', 'bias_5', 'bias_10', 'bias_20']:
                            val = h.get(key)
                            if val != val:  # NaN check: NaN != NaN
                                has_nan = True
                                break
                        if has_nan:
                            continue
                        
                        clean_h = h.copy()
                        # Convert any Timestamp objects to ISO format strings
                        if "date" in clean_h and hasattr(clean_h["date"], "isoformat"):
                            clean_h["date"] = clean_h["date"].isoformat()
                        clean_history.append(clean_h)
                    
                    # Analyze trading patterns
                    pattern_analysis = self._analyze_stock_pattern(stock)
                    
                    stock_entry = {
                        "symbol": stock.get("symbol"),
                        "name": stock.get("name"),
                        "market": stock.get("market"),
                        "current_price": stock.get("current_price"),
                        "change_pct": stock.get("change_pct"),
                        "extra_data": stock.get("extra_data"),
                        "kd_k": stock.get("kd_k"),
                        "kd_d": stock.get("kd_d"),
                        "bias_5": stock.get("bias_5"),
                        "bias_10": stock.get("bias_10"),
                        "bias_20": stock.get("bias_20"),
                        "last_updated": stock.get("last_updated"),
                        "data_points": stock.get("data_points"),
                        # Include last 15 records of history for sparkline charts
                        "history": clean_history,
                        # Add pattern analysis
                        "patterns": pattern_analysis,
                        # Add multi-dimensional score
                        "score": self._serialize_score(stock.get("score")),
                        # Per-stock 外資/投信/自營商買賣超 (None for US stocks / fetch failures)
                        "institutional": stock.get("institutional")
                    }
                    
                    dashboard_data[market].append(stock_entry)
            
            with open(self.stock_data_file, 'w', encoding='utf-8') as f:
                json.dump(dashboard_data, f, indent=2, ensure_ascii=False)
            
            # Log pattern detection summary
            total_patterns = sum(
                len(stock.get("patterns", {}).get("patterns", []))
                for market in ["TW", "US"]
                for stock in dashboard_data.get(market, [])
            )
            logger.info(f"Saved stock data to {self.stock_data_file} (Patterns detected: {total_patterns})")
        except Exception as e:
            logger.error(f"Error saving stock data: {e}")
    
    def get_alert_stats(self) -> Dict:
        """Get statistics about alerts."""
        alerts = self._load_existing_alerts()
        
        # Count by type
        overbought = len([a for a in alerts if a["type"] == "overbought"])
        oversold = len([a for a in alerts if a["type"] == "oversold"])
        
        # Count by market
        tw_alerts = len([a for a in alerts if a.get("market") == "TW"])
        us_alerts = len([a for a in alerts if a.get("market") == "US"])
        
        # Get today's alerts
        today = datetime.now().strftime("%Y-%m-%d")
        today_alerts = len([a for a in alerts if a.get("date") == today])
        
        return {
            "total": len(alerts),
            "overbought": overbought,
            "oversold": oversold,
            "tw_alerts": tw_alerts,
            "us_alerts": us_alerts,
            "today_alerts": today_alerts,
            "active": len([a for a in alerts if not a.get("acknowledged", False)])
        }
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Mark an alert as acknowledged."""
        alerts = self._load_existing_alerts()
        
        for alert in alerts:
            if alert["id"] == alert_id:
                alert["acknowledged"] = True
                alert["acknowledged_at"] = datetime.now().isoformat()
                self._save_alerts(alerts)
                logger.info(f"Alert {alert_id} acknowledged")
                return True
        
        return False


def main():
    """Test the alert checker."""
    # Mock stock data for testing
    test_data = {
        "TW": [
            {"symbol": "2330.TW", "name": "台積電", "market": "TW", "kd_k": 85, "kd_d": 82, "current_price": 550.0},
            {"symbol": "2317.TW", "name": "鴻海", "market": "TW", "kd_k": 45, "kd_d": 48, "current_price": 105.0},
        ],
        "US": [
            {"symbol": "AAPL", "name": "Apple Inc.", "market": "US", "kd_k": 15, "kd_d": 18, "current_price": 175.0},
            {"symbol": "TSLA", "name": "Tesla Inc.", "market": "US", "kd_k": 75, "kd_d": 72, "current_price": 240.0},
        ]
    }
    
    checker = AlertChecker()
    result = checker.process_alerts(test_data)
    
    print("\nAlert Summary:")
    print(json.dumps(result["summary"], indent=2))
    
    print("\nNew Alerts:")
    for alert in result["new_alerts"]:
        print(f"  - {alert['message']}")
    
    print("\nAlert Stats:")
    print(json.dumps(checker.get_alert_stats(), indent=2))


if __name__ == "__main__":
    main()