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
from typing import Dict, Optional

import numpy as np

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fetcher import StockFetcher
from kd_calculator import KDCalculator
from alert_checker import AlertChecker
from scoring_engine import ScoringEngine
from signal_confluence import evaluate_signal_confluence
from market_regime import detect_market_regime
from signal_score import calculate_signal_scores
from tsmc_analyzer import calculate_tsmc_score


class NumpyJSONEncoder(json.JSONEncoder):
    """
    json.dump()'s last line of defense against numpy/pandas scalar types
    (numpy.float64, numpy.int64, numpy.bool_, numpy.ndarray, ...) anywhere in
    the object graph being serialized.

    numpy.float64 happens to be a subclass of Python's float, so it serializes
    fine without this — but numpy.bool_ and numpy.int64 are NOT subclasses of
    Python's bool/int, and comparisons or aggregations across pandas/numpy
    code (fetcher.py, pattern_analyzer.py, scoring_engine.py, kd_calculator.py,
    signal_confluence.py, ...) can produce them in places that are easy to
    miss one-by-one. Rather than chase every individual leak across five
    modules, this catches whatever slips through at the single point it
    actually matters: the moment we're about to write JSON.
    """
    def default(self, obj):
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

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
                    "taiex": {"value": 22350.5, "change": -85.3, "change_pct": -0.38},
                    "us10y": {"value": 4.25, "change": 0.02, "change_pct": 0.47},
                    "dxy": {"value": 104.5, "change": -0.15, "change_pct": -0.14},
                    "fear_greed": {"value": 55, "change": -1.2, "change_pct": -2.13, "label": "Greed"},
                    "btc": {"value": 65000, "change": 780, "change_pct": 1.2},
                    "oil": {"value": 78.5, "change": 0.8, "change_pct": 1.03},
                    "gold": {"value": 2650.0, "change": -12.3, "change_pct": -0.46},
                    "sox": {"value": 5230.0, "change": -45.2, "change_pct": -0.86},
                    "ndx": {"value": 19850.0, "change": 62.5, "change_pct": 0.32},
                    "sp500": {"value": 5450.0, "change": 12.1, "change_pct": 0.22}
                }
                tw_chip_indicators = {
                    "foreign_net": {"value": -40.7, "change": 20.7, "change_pct": 50.86, "unit": "億元", "date": "2026-08-07"},
                    "trust_net": {"value": -12.0, "change": -3.5, "change_pct": -41.18, "unit": "億元", "date": "2026-08-07"},
                    "margin_balance": {"value": 8986438, "change": 28177, "change_pct": 0.31, "unit": "張", "date": "2026-08-07"},
                    "margin_balance_amount": {"value": 5376.6, "change": 48.6, "change_pct": 0.91, "unit": "億元", "date": "2026-08-07"},
                    "short_balance": {"value": 192740, "change": 843, "change_pct": 0.44, "unit": "張", "date": "2026-08-07"},
                    "margin_short_ratio": {"value": 2.15, "change": 0.02, "change_pct": 0.94, "unit": "%"},
                    "usdtwd": {"value": 31.25, "change": -0.05, "change_pct": -0.16},
                    "foreign_futures_net": {"value": -87911, "change": 3204, "change_pct": 3.52, "unit": "口", "date": "2026-08-07"},
                    "put_call_ratio": {"value": 76.92, "change": -2.31, "change_pct": -2.92, "unit": "%", "date": "2026-08-07"},
                    "night_session": {"close": 23100, "prev_close": 23180, "gap": -80,
                                       "gap_pct": -0.35, "date": "2026-08-08", "prev_date": "2026-08-07"}
                }
                market_news = [
                    {"title": "台股收盤大漲逾千點！台積電收2410元 聯發科飆8.5%領軍反攻", "url": "https://tw.stock.yahoo.com/news/example-103500002.html", "meta": "2小時前"},
                    {"title": "美股拉警報？華爾街示警：今夏恐爆三波大修正", "url": "https://tw.stock.yahoo.com/news/example-095923224.html", "meta": "4小時前"},
                    {"title": "日圓兌美元貶破162關口 創40年新低", "url": "https://tw.stock.yahoo.com/news/example-104500542.html", "meta": "6小時前"}
                ]
                tsmc_monthly_revenue = [
                    {"year": 2026, "month": m, "revenue_ntd": 3.3e11 + m * 1.0e10, "report_date": f"2026-{(m % 12) + 1:02d}-10"}
                    for m in range(1, 19)
                ]
                tsmc_quarterly_financials = [
                    {"date": "2026-03-31", "revenue_ntd": 1.134e12, "gross_profit_ntd": 7.513e11, "operating_income_ntd": 6.590e11, "eps": 22.08},
                    {"date": "2026-06-30", "revenue_ntd": 1.270e12, "gross_profit_ntd": 8.598e11, "operating_income_ntd": 7.658e11, "eps": 27.25},
                ]
                tsmc_valuation = [{"date": f"2026-mock-{i}", "per": 28 + (i % 6), "pbr": 10, "dividend_yield": 0.9} for i in range(120)]
                tsmc_official_guidance = {
                    "source": "mock", "fetched_url": "mock",
                    "reported_quarter": "2026Q2", "reported_quarter_end": "2026-06-30",
                    "next_quarter": "2026Q3", "next_quarter_end": "2026-09-30",
                    "actual": {"revenue_usd_b": 40.20, "exchange_rate_usdtwd": 31.60,
                               "gross_margin_pct": 67.7, "operating_margin_pct": 60.3},
                    "guidance_for_reported_quarter": {
                        "revenue_low_usd_b": 39.0, "revenue_high_usd_b": 40.2, "exchange_rate_assumed": 31.7,
                        "gross_margin_low_pct": 65.5, "gross_margin_high_pct": 67.5,
                        "operating_margin_low_pct": 56.5, "operating_margin_high_pct": 58.5},
                    "guidance_for_next_quarter": {
                        "revenue_low_usd_b": 44.6, "revenue_high_usd_b": 45.8, "exchange_rate_assumed": 32.0,
                        "gross_margin_low_pct": 65.0, "gross_margin_high_pct": 67.0,
                        "operating_margin_low_pct": 56.0, "operating_margin_high_pct": 58.0},
                }
                logger.info("Using mock data (test mode)")
            else:
                stock_data = self.fetcher.fetch_all_stocks()
                macro_indicators = self.fetcher.fetch_macro_indicators()
                tw_chip_indicators = self.fetcher.fetch_tw_chip_indicators()
                try:
                    market_news = self.fetcher.fetch_market_news()
                except Exception as e:
                    logger.error(f"Market news fetch failed (non-fatal, continuing): {e}")
                    market_news = []
                try:
                    tsmc_monthly_revenue = self.fetcher.fetch_tsmc_monthly_revenue()
                    tsmc_quarterly_financials = self.fetcher.fetch_tsmc_quarterly_financials()
                    tsmc_valuation = self.fetcher.fetch_tsmc_valuation()
                except Exception as e:
                    logger.error(f"TSMC fundamentals fetch failed (non-fatal, continuing): {e}")
                    tsmc_monthly_revenue, tsmc_quarterly_financials, tsmc_valuation = [], [], []
                try:
                    tsmc_official_guidance = self.fetcher.fetch_tsmc_official_guidance()
                except Exception as e:
                    logger.error(f"TSMC official guidance fetch failed (non-fatal, continuing): {e}")
                    tsmc_official_guidance = None

            stocks_fetched = sum(len(stocks) for stocks in stock_data.values())
            logger.info(f"Fetched data for {stocks_fetched} stocks and macro indicators")
            
            # Step 2: Calculate KD indicators
            logger.info("\n[Step 2/4] Calculating KD indicators...")
            stocks_with_kd = self.calculator.calculate_all_stocks(stock_data)

            stocks_calculated = sum(len(stocks) for stocks in stocks_with_kd.values())
            logger.info(f"Calculated KD for {stocks_calculated} stocks")

            # Step 2.25: Per-stock 外資/投信/自營商買賣超 (individual-holding
            # institutional flow) — the per-stock counterpart to the market-wide
            # foreign_net/trust_net already in tw_chip_indicators. Runs after KD
            # calc (calculate_all_stocks rebuilds each stock dict, so anything
            # attached before that point would be lost) and feeds both the alert
            # filters (Step 3) and the dashboard's per-stock cards.
            logger.info("\n[Step 2.25/4] Fetching per-stock institutional flow...")
            if test_mode:
                for stock in stocks_with_kd.get("TW", []):
                    stock["institutional"] = {
                        "date": "2026-08-07", "foreign_net": 850000, "foreign_net_prev": -320000,
                        "trust_net": 120000, "dealer_net": -45000, "foreign_net_3d": 1560000
                    }
            else:
                self.fetcher.attach_stock_institutional_flow(stocks_with_kd)

            # Step 2.5: Calculate multi-dimensional scores
            logger.info("\n[Step 2.5/4] Calculating multi-dimensional scores...")
            for market in stocks_with_kd:
                for stock in stocks_with_kd[market]:
                    if "error" not in stock:
                        score_result = self.scorer.calculate(stock)
                        stock["score"] = score_result
            logger.info("Multi-dimensional scoring complete")
            
            # Step 2.75: Persist today's macro/chip snapshot, then evaluate the
            # top/bottom signal-confluence model, the 0-100 signal scores, and
            # the market regime against the accumulated history. This has to
            # run BEFORE Step 3 (alert checking) — the regime label is fed
            # into each stock's KD filter confirmation (see
            # alert_checker.AlertChecker._evaluate_filters's `regime` param),
            # so it needs to already be known by the time alerts are checked,
            # not computed afterward as a separate side-channel.
            logger.info("\n[Step 2.75/4] Updating macro history, signal confluence, regime, and scores...")
            macro_history = self._save_macro_history(macro_indicators, tw_chip_indicators, test_mode=test_mode)
            confluence_result = evaluate_signal_confluence(macro_history)
            regime_result = detect_market_regime(macro_history)
            signal_score_result = calculate_signal_scores(macro_history)
            logger.info(f"Signal confluence: available={confluence_result['available']}, "
                        f"history_days={confluence_result.get('history_days')}")
            logger.info(f"Market regime: {regime_result.get('regime')} "
                        f"({regime_result.get('regime_label')}), available={regime_result.get('available')}")

            # Step 2.85: 台積電 (2330) five-layer Investment Score — needs
            # regime_result/confluence_result (just computed above, for the
            # Market Regime dimension and the Panic Reversal buy-point) and
            # stocks_with_kd's per-stock score/institutional data (Step 2.5/
            # 2.25, already done).
            #
            # Guidance data itself now comes primarily from
            # tsmc_official_guidance (Step 1's auto-fetch of TSMC's own IR
            # site — Level A official Guidance, per the three-tier data
            # design). data/tsmc_guidance.json remains as a manually-seeded
            # fallback for quarters before the auto-fetch existed; auto
            # always wins on an overlapping quarter. See
            # _update_tsmc_guidance_auto()'s docstring for why past auto
            # entries are never overwritten (avoids look-ahead/backfill
            # bias — each entry is frozen at what was true when first seen).
            logger.info("\n[Step 2.85/4] Calculating TSMC (2330) investment score...")
            try:
                stock_2330 = next((s for s in stocks_with_kd.get("TW", []) if s.get("symbol") == "2330.TW" and "error" not in s), None)
                stock_tsm = next((s for s in stocks_with_kd.get("US", []) if s.get("symbol") == "TSM" and "error" not in s), None)
                usdtwd = tw_chip_indicators.get("usdtwd", {}).get("value")
                guidance_entries, actual_vs_guidance = self._update_tsmc_guidance_auto(tsmc_official_guidance)
                if stock_2330 is None:
                    logger.warning("2330.TW not found in watchlist results — skipping TSMC score")
                    tsmc_analysis = {"available": False, "reason": "2330.TW not in stocks_with_kd"}
                else:
                    tsmc_analysis = calculate_tsmc_score(
                        tsmc_monthly_revenue, tsmc_quarterly_financials, tsmc_valuation, guidance_entries,
                        stock_2330, stock_tsm, macro_history, regime_result, confluence_result, usdtwd,
                        actual_vs_guidance=actual_vs_guidance
                    )
                logger.info(f"TSMC score: available={tsmc_analysis.get('available')}, total={tsmc_analysis.get('total')}")
            except Exception as e:
                logger.error(f"TSMC score calculation failed (non-fatal, continuing): {e}", exc_info=True)
                tsmc_analysis = {"available": False, "reason": str(e)}

            # Step 3: Check for alerts (regime-aware — see Step 2.75 note above)
            logger.info("\n[Step 3/4] Checking for alerts...")
            current_regime = regime_result.get("regime") if regime_result.get("available") else None
            alert_result = self.checker.process_alerts(stocks_with_kd, regime=current_regime)

            # Step 4: Generate summary report
            logger.info("\n[Step 4/4] Generating summary report...")
            summary = self._generate_summary(stocks_with_kd, alert_result, macro_indicators,
                                              tw_chip_indicators, confluence_result, market_news,
                                              regime_result, signal_score_result, tsmc_analysis)
            
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
    
    def _generate_summary(self, stocks_data: Dict, alert_result: Dict, macro_indicators: Dict = None,
                           tw_chip_indicators: Dict = None, confluence_result: Dict = None,
                           market_news: list = None, regime_result: Dict = None,
                           signal_score_result: Dict = None, tsmc_analysis: Dict = None) -> Dict:
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
            "chip": tw_chip_indicators or {},
            "signal_confluence": confluence_result or {"available": False},
            "market_regime": regime_result or {"available": False},
            "signal_score": signal_score_result or {"available": False},
            "tsmc_analysis": tsmc_analysis or {"available": False},
            "news": market_news or [],
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
            json.dump(summary, f, indent=2, ensure_ascii=False, cls=NumpyJSONEncoder)
        
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
            json.dump(logs, f, indent=2, ensure_ascii=False, cls=NumpyJSONEncoder)

    def _load_tsmc_guidance(self) -> list:
        """
        Load the manually-maintained TSMC guidance history (see
        data/tsmc_guidance.json's own "_readme" field for why this one file
        is hand-edited instead of fetched — no free API publishes TSMC's own
        structured guidance figures or Street consensus estimates). Read
        only; main.py never writes to this file. Returns [] (not an error)
        if the file doesn't exist yet, so a fresh checkout without it
        degrades to tsmc_analyzer.py's normal "insufficient data" handling
        for the Guidance dimension rather than crashing the whole run.
        """
        guidance_file = os.path.join(self.data_dir, 'tsmc_guidance.json')
        if os.path.exists(guidance_file):
            try:
                with open(guidance_file, 'r', encoding='utf-8') as f:
                    return json.load(f).get("entries", [])
            except Exception as e:
                logger.warning(f"Could not load tsmc_guidance.json: {e}")
        return []

    def _update_tsmc_guidance_auto(self, official_guidance: Optional[dict]) -> tuple:
        """
        Persist and merge the auto-fetched TSMC official Guidance
        (fetcher.fetch_tsmc_official_guidance(), Step 1) into a running
        history file, then merge it with the manually-seeded
        data/tsmc_guidance.json to build the final guidance_entries list
        tsmc_analyzer.py's _score_guidance() consumes.

        Persistence design (data/tsmc_guidance_auto.json):
          - "guidance_history": one entry per quarter's newly-issued
            forward guidance (what data/tsmc_guidance.json's manual
            entries already looked like) — newest first.
          - "actual_vs_guidance_history": one entry per quarter's realized
            actual vs. the guidance that had been given FOR that quarter —
            newest first. This is what makes the beat/miss calculation
            exact (both figures already in USD, straight from TSMC's own
            page) instead of the old FinMind NTD-actual + same-day-FX-
            snapshot approximation.

        Past entries are NEVER overwritten once written — each quarter's
        entry is frozen at whatever the page showed the first time this
        pipeline saw that quarter as "latest". This matters for the same
        point-in-time-integrity reason the project owner raised about
        Consensus data: if this file were instead rebuilt by re-fetching
        and blindly upserting on every hourly run, a > later > revision to
        TSMC's own historical figures (restatements are rare but do
        happen) could silently rewrite what a past backtest would have
        seen "as of" that date. Append-only-by-new-quarter avoids that.

        Returns (guidance_entries, actual_vs_guidance_latest):
          - guidance_entries: auto history + manual data/tsmc_guidance.json
            entries, deduped by quarter (auto wins), sorted newest-first —
            drop-in compatible with the pre-existing guidance_entries shape.
          - actual_vs_guidance_latest: the newest actual_vs_guidance_history
            entry (or None), passed straight to calculate_tsmc_score() for
            the precise beat/miss path.
        """
        auto_file = os.path.join(self.data_dir, 'tsmc_guidance_auto.json')
        auto_data = {"guidance_history": [], "actual_vs_guidance_history": []}
        if os.path.exists(auto_file):
            try:
                with open(auto_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    auto_data["guidance_history"] = loaded.get("guidance_history", [])
                    auto_data["actual_vs_guidance_history"] = loaded.get("actual_vs_guidance_history", [])
            except Exception as e:
                logger.warning(f"Could not load tsmc_guidance_auto.json: {e}")

        if official_guidance:
            fetched_at = datetime.now().isoformat()
            gnq = official_guidance.get("guidance_for_next_quarter", {})
            new_guidance_entry = {
                "quarter": official_guidance.get("next_quarter"),
                "guidance_given_date_approx": fetched_at[:10],
                "guidance_given_for_quarter_end": official_guidance.get("next_quarter_end"),
                "revenue_guidance_low_usd_b": gnq.get("revenue_low_usd_b"),
                "revenue_guidance_high_usd_b": gnq.get("revenue_high_usd_b"),
                "exchange_rate_guidance": gnq.get("exchange_rate_assumed"),
                "gross_margin_guidance_low_pct": gnq.get("gross_margin_low_pct"),
                "gross_margin_guidance_high_pct": gnq.get("gross_margin_high_pct"),
                "operating_margin_guidance_low_pct": gnq.get("operating_margin_low_pct"),
                "operating_margin_guidance_high_pct": gnq.get("operating_margin_high_pct"),
                "capex_guidance_usd_b": None,
                "benchmark_type": "GUIDANCE",
                "source": f"auto:{official_guidance.get('source')}",
                "notes": f"{official_guidance.get('reported_quarter')}法說會公布之"
                         f"{official_guidance.get('next_quarter')}財測指引（自動抓取，"
                         f"guidance_given_date_approx為抓取當下日期，非確切法說會日期）",
            }
            existing_quarters = {e.get("quarter") for e in auto_data["guidance_history"]}
            if new_guidance_entry["quarter"] not in existing_quarters:
                auto_data["guidance_history"].insert(0, new_guidance_entry)
                logger.info(f"TSMC guidance auto-fetch: recorded new quarter "
                            f"{new_guidance_entry['quarter']}")

            act = official_guidance.get("actual", {})
            grq = official_guidance.get("guidance_for_reported_quarter", {})
            new_actual_entry = {
                "quarter": official_guidance.get("reported_quarter"),
                "quarter_end": official_guidance.get("reported_quarter_end"),
                "actual_revenue_usd_b": act.get("revenue_usd_b"),
                "guidance_revenue_low_usd_b": grq.get("revenue_low_usd_b"),
                "guidance_revenue_high_usd_b": grq.get("revenue_high_usd_b"),
                "actual_gross_margin_pct": act.get("gross_margin_pct"),
                "guidance_gross_margin_low_pct": grq.get("gross_margin_low_pct"),
                "guidance_gross_margin_high_pct": grq.get("gross_margin_high_pct"),
                "actual_operating_margin_pct": act.get("operating_margin_pct"),
                "guidance_operating_margin_low_pct": grq.get("operating_margin_low_pct"),
                "guidance_operating_margin_high_pct": grq.get("operating_margin_high_pct"),
                "actual_exchange_rate": act.get("exchange_rate_usdtwd"),
                "guidance_exchange_rate": grq.get("exchange_rate_assumed"),
                "benchmark_type": "GUIDANCE",
                "source": f"auto:{official_guidance.get('source')}",
                "fetched_at": fetched_at,
            }
            existing_actual_quarters = {e.get("quarter") for e in auto_data["actual_vs_guidance_history"]}
            if new_actual_entry["quarter"] not in existing_actual_quarters:
                auto_data["actual_vs_guidance_history"].insert(0, new_actual_entry)
                logger.info(f"TSMC guidance auto-fetch: recorded actual-vs-guidance for "
                            f"{new_actual_entry['quarter']}")

            try:
                with open(auto_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "_readme": ("自動抓取台積電官方IR網站（investor.tsmc.com/english/quarterly-results）"
                                    "之Guidance/Actual資料。每次pipeline執行時抓取當下最新一季，若該季尚未"
                                    "記錄過才寫入（append-only，不覆寫已記錄的舊季別，避免回填偏誤）。"
                                    "guidance_history為公司新公布的下一季財測指引；"
                                    "actual_vs_guidance_history為已公布實際數字對比當初該季指引之beat/miss，"
                                    "兩者數字皆為公司官方US$計價數字，無需自行以NTD/USD匯率換算。"
                                    "benchmark_type恆為\"GUIDANCE\"——與第三方分析師Consensus（若未來加入）"
                                    "絕不可混用比較。"),
                        "guidance_history": auto_data["guidance_history"],
                        "actual_vs_guidance_history": auto_data["actual_vs_guidance_history"],
                        "last_fetch_ok": True,
                        "last_fetch_at": fetched_at,
                    }, f, indent=2, ensure_ascii=False, cls=NumpyJSONEncoder)
            except Exception as e:
                logger.warning(f"Could not save tsmc_guidance_auto.json: {e}")
        else:
            logger.warning("TSMC official guidance fetch returned nothing this run — "
                            "using previously-persisted auto history (if any) + manual fallback")

        manual_entries = self._load_tsmc_guidance()
        merged_by_quarter = {}
        for e in manual_entries:
            q = e.get("quarter")
            if q:
                merged_by_quarter[q] = e
        for e in auto_data["guidance_history"]:
            q = e.get("quarter")
            if q:
                merged_by_quarter[q] = e  # auto wins over manual on the same quarter
        guidance_entries = sorted(merged_by_quarter.values(), key=lambda e: e.get("quarter", ""), reverse=True)

        actual_vs_guidance_latest = auto_data["actual_vs_guidance_history"][0] if auto_data["actual_vs_guidance_history"] else None
        return guidance_entries, actual_vs_guidance_latest

    def _load_macro_history(self) -> list:
        """Load the persisted daily macro/chip snapshot history."""
        history_file = os.path.join(self.data_dir, 'macro_history.json')
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load macro_history.json: {e}")
        return []

    @staticmethod
    def _to_native(value):
        """
        Coerce numpy/pandas scalar types (numpy.float64, numpy.bool_, ...) to
        plain Python types before they enter history that gets JSON-persisted
        or compared against JSON-loaded (already-plain) values.

        Why this matters: fetcher.py's round(pandas_series_value, N) returns a
        numpy.float64, not a plain float. That's harmless on its own — float64
        IS a subclass of Python's float, so json.dump() serializes it fine —
        but a numpy.float64 (today's fresh value) compared against a plain
        float (a prior day's value, already round-tripped through JSON) via
        >, >=, < produces numpy.bool_, NOT Python bool. json.dump() can't
        serialize numpy.bool_ ("Object of type bool is not JSON serializable"
        — numpy 2.x's repr for numpy.bool_ is literally "bool", so the error
        looks like it's complaining about an ordinary bool). Converting here,
        at the point values enter persisted history, stops the numpy type
        from ever reaching a comparison in signal_confluence.py.
        """
        if value is None:
            return None
        if hasattr(value, "item"):
            return value.item()
        return value

    def _merge_backfill(self, history: list, backfill: Dict[str, Dict]) -> list:
        """
        Merge a fetcher.backfill_macro_history() result into the existing daily
        history, filling gaps only. Never overwrites a value that's already
        recorded — a real value from a normal run (today's included) always
        wins over a historical backfill value for the same date/field.
        """
        by_date = {h["date"]: h for h in history if h.get("date")}
        for date_str, fields in backfill.items():
            if date_str in by_date:
                entry = by_date[date_str]
                for k, v in fields.items():
                    if entry.get(k) is None:
                        entry[k] = v
            else:
                new_entry = {"date": date_str}
                new_entry.update(fields)
                history.append(new_entry)
                by_date[date_str] = new_entry
        history.sort(key=lambda h: h.get("date") or "")
        return history[-250:]

    def _enrich_chip_changes(self, tw_chip_indicators: Dict, history: list, snapshot_date: str):
        """
        Add change / change_pct (vs. the most recent prior trading day in
        history) to chip fields that don't already carry one from fetcher.py.
        Mutates tw_chip_indicators in place.

        change_pct is computed as change / abs(prev_value) rather than the
        textbook change / prev_value, so its sign always matches change's
        sign. This matters specifically for foreign_net/trust_net, which are
        net buy/sell amounts that regularly cross zero (e.g. -40.7 -> -20.0
        is an improvement/less selling — dividing by the raw negative prev
        value would flip that into a misleading negative percentage).
        """
        prior = next((h for h in reversed(history) if h.get("date") and h["date"] < snapshot_date), None)
        if not prior:
            return

        # (chip key, history key, rounding decimals)
        fields_to_enrich = [
            ("foreign_net", "foreign_net", 2),
            ("trust_net", "trust_net", 2),
            ("foreign_futures_net", "foreign_futures_net", 0),
            ("put_call_ratio", "put_call_ratio", 2),
        ]
        for chip_key, hist_key, decimals in fields_to_enrich:
            field = tw_chip_indicators.get(chip_key)
            if not isinstance(field, dict) or field.get("value") is None:
                continue
            if field.get("change") is not None:
                continue  # fetcher.py already computed this one
            prev_val = prior.get(hist_key)
            if prev_val is None:
                continue
            change = field["value"] - prev_val
            field["change"] = round(change, decimals)
            field["change_pct"] = round(change / abs(prev_val) * 100, 2) if prev_val else None

    def _save_macro_history(self, macro_indicators: Dict, tw_chip_indicators: Dict,
                             test_mode: bool = False) -> list:
        """
        Append (or update) today's macro + TW chip-flow snapshot to a running daily
        history file. This is what lets trend-based signal-confluence checks (DXY
        breaking above a prior high, VIX peaking and rolling over, margin balance
        dropping several days in a row, etc.) actually work — a single point-in-time
        reading can't tell you a trend, you need history to compare against.

        Chip data (foreign_net, margin_balance, ...) is End-of-Day and carries its
        own report date (which trading day it's actually for) that can lag "today"
        if called before TWSE posts that day's numbers. macro data (DXY/VIX/US10Y
        from yfinance) doesn't carry an explicit date, so we fall back to the chip
        report date when available, else today's date. Re-running within the same
        day (hourly schedule) overwrites that day's entry instead of duplicating it.

        If history is still short (signal confluence needs ~21 trading days), this
        also runs a one-time historical backfill (see fetcher.backfill_macro_history)
        instead of waiting three weeks of hourly runs to accumulate it day by day.
        A marker file gates this to run at most once — even if the backfill only
        partially succeeds, we don't want every hourly run for the next three weeks
        re-hitting TWSE with ~70 sequential requests. Delete
        data/.macro_backfill_done to force a retry.

        Returns the updated history list (so run() can pass it straight into the
        signal confluence evaluator without a redundant re-read from disk).
        """
        history_file = os.path.join(self.data_dir, 'macro_history.json')
        history = self._load_macro_history()

        backfill_marker = os.path.join(self.data_dir, '.macro_backfill_done')
        if not test_mode and len(history) < 21 and not os.path.exists(backfill_marker):
            try:
                logger.info("Macro history is short — running one-time historical backfill...")
                backfill = self.fetcher.backfill_macro_history()
                history = self._merge_backfill(history, backfill)
                logger.info(f"Backfill merged {len(backfill)} historical dates; history now {len(history)} days")
            except Exception as e:
                logger.warning(f"Macro history backfill failed (will keep accumulating day-by-day): {e}")
            finally:
                try:
                    with open(backfill_marker, 'w') as f:
                        f.write(datetime.now().isoformat())
                except Exception as e:
                    logger.warning(f"Could not write backfill marker: {e}")

        snapshot_date = (
            tw_chip_indicators.get("foreign_net", {}).get("date")
            or tw_chip_indicators.get("margin_balance", {}).get("date")
            or datetime.now().strftime("%Y-%m-%d")
        )

        # foreign_net/trust_net (BFI82U) and foreign_futures_net/put_call_ratio
        # (FinMind) come back as single-day snapshots with no prior-day value
        # embedded in the API response (unlike margin/short/usdtwd, which are
        # enriched with change/change_pct directly in fetcher.py from data
        # that's already in the same response). For these four, the only
        # place a prior value is available is yesterday's persisted history
        # entry, so enrich them here, in place, before today's entry is built
        # — this way summary.json's "chip" payload carries change/change_pct
        # for every field, not just the ones fetcher.py could compute alone.
        self._enrich_chip_changes(tw_chip_indicators, history, snapshot_date)

        entry = {
            "date": snapshot_date,
            "taiex": self._to_native(macro_indicators.get("taiex", {}).get("value")),
            "dxy": self._to_native(macro_indicators.get("dxy", {}).get("value")),
            "us10y": self._to_native(macro_indicators.get("us10y", {}).get("value")),
            "vix": self._to_native(macro_indicators.get("fear_greed", {}).get("value")),
            "usdtwd": self._to_native(tw_chip_indicators.get("usdtwd", {}).get("value")),
            "foreign_net": self._to_native(tw_chip_indicators.get("foreign_net", {}).get("value")),
            "trust_net": self._to_native(tw_chip_indicators.get("trust_net", {}).get("value")),
            "margin_balance": self._to_native(tw_chip_indicators.get("margin_balance", {}).get("value")),
            "margin_balance_amount": self._to_native(tw_chip_indicators.get("margin_balance_amount", {}).get("value")),
            "foreign_futures_net": self._to_native(tw_chip_indicators.get("foreign_futures_net", {}).get("value")),
            "put_call_ratio": self._to_native(tw_chip_indicators.get("put_call_ratio", {}).get("value")),
            "sox": self._to_native(macro_indicators.get("sox", {}).get("value")),
            "ndx": self._to_native(macro_indicators.get("ndx", {}).get("value")),
            "sp500": self._to_native(macro_indicators.get("sp500", {}).get("value")),
            "night_session_gap_pct": self._to_native(tw_chip_indicators.get("night_session", {}).get("gap_pct")),
        }

        # Overwrite today's entry if we already have one (hourly reruns), else append
        existing_idx = next((i for i, h in enumerate(history) if h.get("date") == snapshot_date), None)
        if existing_idx is not None:
            history[existing_idx] = entry
        else:
            history.append(entry)

        history.sort(key=lambda h: h.get("date") or "")
        # Keep roughly a year of trading days
        history = history[-250:]

        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False, cls=NumpyJSONEncoder)

        return history


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
