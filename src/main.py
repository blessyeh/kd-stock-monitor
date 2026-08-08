#!/usr/bin/env python3
"""
Main Orchestrator - Daily runner for KD Stock Monitor.

This script orchestrates the entire workflow:
1. Fetch stock data from Yahoo Finance
2. Calculate KD indicators
3. Check for alerts
4. Save results for dashboard
"""

import os
import sys
import json
import argparse
from datetime import datetime
import logging
from typing import Dict

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fetcher import StockFetcher
from kd_calculator import KDCalculator
from alert_checker import AlertChecker
from scoring_engine import ScoringEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class KDStockMonitor:
    """Main orchestrator for the KD Stock Monitoring system."""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize the monitor with configuration."""
        self.config_path = config_path
        self.fetcher = StockFetcher(config_path)
        self.calculator = KDCalculator(config_path)
        self.checker = AlertChecker(config_path)
        self.scorer = ScoringEngine()
        
        # Ensure data directory exists
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
        os.makedirs(self.data_dir, exist_ok=True)
    
    def run(self, test_mode: bool = False) -> Dict:
        """
        Run the complete monitoring workflow.
        
        Args:
            test_mode: If True, use mock data instead of fetching real data
        
        Returns:
            Dictionary with execution results
        """
        start_time = datetime.now()
        logger.info("="*60)
        logger.info("KD Stock Monitor - Starting Run")
        logger.info("="*60)
        
        try:
            # Step 1: Fetch stock data and macro indicators
            logger.info("\n[Step 1/4] Fetching stock data and macro indicators...")
            if test_mode:
                stock_data = self._get_mock_data()
                macro_indicators = {
                    "us10y": {"value": 4.25, "change": 0.02},
                    "dxy": {"value": 104.5, "change": -0.15},
                    "fear_greed": {"value": 55, "label": "Greed"},
                    "btc": {"value": 65000, "change_pct": 1.2},
                    "oil": {"value": 78.5, "change": 0.8, "change_pct": 1.03},
                    "gold": {"value": 2650.0, "change": -12.3, "change_pct": -0.46}
                }
                logger.info("Using mock data (test mode)")
            else:
                stock_data = self.fetcher.fetch_all_stocks()
                macro_indicators = self.fetcher.fetch_macro_indicators()
            
            stocks_fetched = sum(len(stocks) for stocks in stock_data.values())
            logger.info(f"Fetched data for {stocks_fetched} stocks and macro indicators")
            
            # Step 2: Calculate KD indicators
            logger.info("\n[Step 2/4] Calculating KD indicators...")
            stocks_with_kd = self.calculator.calculate_all_stocks(stock_data)
            
            stocks_calculated = sum(len(stocks) for stocks in stocks_with_kd.values())
            logger.info(f"Calculated KD for {stocks_calculated} stocks")
            
            # Step 2.5: Calculate multi-dimensional scores
            logger.info("\n[Step 2.5/4] Calculating multi-dimensional scores...")
            for market in stocks_with_kd:
                for stock in stocks_with_kd[market]:
                    if "error" not in stock:
                        score_result = self.scorer.calculate(stock)
                        stock["score"] = score_result
            logger.info("Multi-dimensional scoring complete")
            
            # Step 3: Check for alerts
            logger.info("\n[Step 3/4] Checking for alerts...")
            alert_result = self.checker.process_alerts(stocks_with_kd)
            
            # Step 4: Generate summary report
            logger.info("\n[Step 4/4] Generating summary report...")
            summary = self._generate_summary(stocks_with_kd, alert_result, macro_indicators)
            
            # Save run log
            self._save_run_log(summary)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info("\n" + "="*60)
            logger.info(f"Run completed in {duration:.2f} seconds")
            logger.info(f"Stocks processed: {summary['stocks_processed']}")
            logger.info(f"New alerts: {summary['new_alerts']}")
            logger.info(f"Overbought: {summary['overbought_count']}")
            logger.info(f"Oversold: {summary['oversold_count']}")
            logger.info("="*60)
            
            return {
                "success": True,
                "duration_seconds": duration,
                "summary": summary,
                "alert_result": alert_result
            }
            
        except Exception as e:
            logger.error(f"Error during execution: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_mock_data(self) -> Dict:
        """Generate mock data for testing."""
        import pandas as pd
        import numpy as np
        
        mock_data = {"TW": [], "US": []}
        
        for market in ["TW", "US"]:
            stocks = self.fetcher.config["stocks"][market]
            for stock in stocks:
                # Generate mock price data
                dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
                base_price = np.random.uniform(50, 500)
                prices = base_price + np.cumsum(np.random.randn(30) * 2)
                
                df = pd.DataFrame({
                    'date': dates,
                    'open': prices - np.random.rand(30) * 2,
                    'high': prices + np.random.rand(30) * 3,
                    'low': prices - np.random.rand(30) * 3,
                    'close': prices,
                    'volume': np.random.randint(1000000, 10000000, 30)
                })
                
                mock_data[market].append({
                    "symbol": stock["symbol"],
                    "name": stock["name"],
                    "market": market,
                    "data": df,
                    "last_updated": datetime.now().isoformat()
                })
        
        return mock_data
    
    def _generate_summary(self, stocks_data: Dict, alert_result: Dict, macro_indicators: Dict = None) -> Dict:
        """Generate a summary of the run."""
        all_stocks = []
        for market in ["TW", "US"]:
            all_stocks.extend(stocks_data.get(market, []))
        
        # Count stocks by status
        overbought_stocks = []
        oversold_stocks = []
        normal = []
        errors = []
        
        thresholds = self.checker.thresholds
        
        for stock in all_stocks:
            if "error" in stock:
                errors.append(stock)
                continue
            
            kd_k = stock.get("kd_k")
            kd_d = stock.get("kd_d")
            
            if kd_k is None or kd_d is None:
                errors.append(stock)
                continue
            
            stock_summary = {
                "symbol": stock["symbol"], 
                "name": stock["name"], 
                "current_price": stock.get("current_price"),
                "change_pct": stock.get("change_pct"),
                "extra_data": stock.get("extra_data"),
                "kd_k": kd_k, 
                "kd_d": kd_d
            }
            
            if kd_k >= thresholds["overbought"] or kd_d >= thresholds["overbought"]:
                overbought_stocks.append(stock_summary)
            elif kd_k <= thresholds["oversold"] or kd_d <= thresholds["oversold"]:
                oversold_stocks.append(stock_summary)
            else:
                normal.append(stock)
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "macro": macro_indicators or {},
            "stocks_processed": len(all_stocks),
            "stocks_successful": len([s for s in all_stocks if "error" not in s]),
            "stocks_failed": len(errors),
            "new_alerts": alert_result["summary"]["new_alerts"],
            "overbought_count": len(overbought_stocks),
            "oversold_count": len(oversold_stocks),
            "normal_count": len(normal),
            "overbought_stocks": overbought_stocks,
            "oversold_stocks": oversold_stocks,
            "errors": [{"symbol": s["symbol"], "error": s.get("error", "Unknown error")} for s in errors]
        }
        
        # Save summary to file
        summary_file = os.path.join(self.data_dir, 'summary.json')
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        return summary
    
    def _save_run_log(self, summary: Dict):
        """Save run log for historical tracking."""
        log_file = os.path.join(self.data_dir, 'run_log.json')
        
        # Load existing logs
        logs = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        # Add new log entry
        log_entry = {
            "timestamp": summary["timestamp"],
            "date": summary["date"],
            "stocks_processed": summary["stocks_processed"],
            "new_alerts": summary["new_alerts"],
            "overbought": summary["overbought_count"],
            "oversold": summary["oversold_count"]
        }
        
        logs.append(log_entry)
        
        # Keep only last 30 days of logs
        logs = logs[-30:]
        
        # Save logs
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='KD Stock Monitor - Daily runner')
    parser.add_argument('--test', action='store_true', help='Run in test mode with mock data')
    parser.add_argument('--config', default='config.json', help='Path to config file')
    args = parser.parse_args()
    
    # Change to script directory for relative paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(os.path.join(script_dir, '..'))
    
    # Run the monitor
    monitor = KDStockMonitor(args.config)
    result = monitor.run(test_mode=args.test)
    
    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
