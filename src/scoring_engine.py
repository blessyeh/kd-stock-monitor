#!/usr/bin/env python3
"""
Scoring Engine - Multi-dimensional stock scoring system
Calculates RSI, MA Bias, MACD, Volume-Price, Trend from historical OHLCV data
"""

import numpy as np
import logging
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ScoringEngine:
    """Multi-dimensional stock scoring system"""

    def __init__(self):
        self.weights = {
            'kd': 0.20,
            'rsi': 0.15,
            'ma_bias': 0.15,
            'macd': 0.15,
            'volume_price': 0.15,
            'trend': 0.20,
        }

    def calculate(self, stock: Dict) -> Dict:
        """Calculate full score for a single stock from its history"""
        history = stock.get('history', [])
        if len(history) < 30:
            return self._empty_score()

        try:
            closes = np.array([h['close'] for h in history])
            highs = np.array([h['high'] for h in history])
            lows = np.array([h['low'] for h in history])
            volumes = np.array([h['volume'] for h in history])
            opens = np.array([h['open'] for h in history])
        except (KeyError, TypeError):
            return self._empty_score()

        kd_k = stock.get('kd_k')
        kd_d = stock.get('kd_d')

        scores = {}
        details = {}

        # 1. KD Momentum (already computed)
        if kd_k is not None and kd_d is not None:
            kd_score = self._score_kd(kd_k, kd_d)
            scores['kd'] = kd_score
            details['kd'] = {'score': kd_score, 'k': kd_k, 'd': kd_d}
        else:
            scores['kd'] = 50
            details['kd'] = {'score': 50, 'k': None, 'd': None}

        # 2. RSI
        rsi = self._calculate_rsi(closes)
        rsi_score = self._score_rsi(rsi)
        scores['rsi'] = rsi_score
        details['rsi'] = {'score': rsi_score, 'value': rsi}

        # 3. MA Bias (deviation from MA20/MA60)
        ma_bias_score, ma_bias_detail = self._score_ma_bias(closes)
        scores['ma_bias'] = ma_bias_score
        details['ma_bias'] = {'score': ma_bias_score, **ma_bias_detail}

        # 4. MACD
        macd_score, macd_detail = self._score_macd(closes)
        scores['macd'] = macd_score
        details['macd'] = {'score': macd_score, **macd_detail}

        # 5. Volume-Price
        vp_score, vp_detail = self._score_volume_price(opens, highs, lows, closes, volumes)
        scores['volume_price'] = vp_score
        details['volume_price'] = {'score': vp_score, **vp_detail}

        # 6. Trend (ADX-like from price slope + volatility)
        trend_score, trend_detail = self._score_trend(closes, volumes)
        scores['trend'] = trend_score
        details['trend'] = {'score': trend_score, **trend_detail}

        # 7. Bollinger Bands — informational only (not weighted into `total`),
        # used by alert_checker.py as a mean-reversion confirmation filter
        # alongside the MA/volume/MACD filters: a KD<=20 reading that also
        # touches the lower band has a statistically higher bounce rate than
        # KD<=20 alone, and a KD>=80 reading that touches the upper band
        # without volume confirmation flags short-term exhaustion.
        bb_detail = self._calc_bollinger(closes)
        details['bollinger'] = bb_detail

        # Weighted total
        total = sum(scores[k] * self.weights[k] for k in self.weights)
        total = round(min(100, max(0, total)), 1)

        # Recommendation
        recommendation = self._recommendation(total)

        return {
            'total': total,
            'recommendation': recommendation,
            'details': details,
            'raw': {
                'rsi': rsi,
                'ma20': ma_bias_detail.get('ma20'),
                'ma60': ma_bias_detail.get('ma60'),
                'macd_hist': macd_detail.get('macd_hist'),
                'macd_hist_prev': macd_detail.get('macd_hist_prev'),
                'volume_ratio': vp_detail.get('volume_ratio'),
                'slope_20d': trend_detail.get('slope_20d'),
                'trend_dir': trend_detail.get('trend_dir'),
                'bb_upper': bb_detail.get('bb_upper'),
                'bb_lower': bb_detail.get('bb_lower'),
                'percent_b': bb_detail.get('percent_b'),
            }
        }

    def _empty_score(self) -> Dict:
        """Return empty score when data insufficient"""
        return {
            'total': 50,
            'recommendation': '觀望',
            'details': {k: {'score': 50} for k in self.weights},
            'raw': {}
        }

    # ── KD Scoring ──────────────────────────────
    @staticmethod
    def _score_kd(k: float, d: float) -> float:
        """KD score: lower K = more oversold = higher buy score"""
        avg = (k + d) / 2
        if avg <= 15:
            return 100
        elif avg <= 25:
            return 90
        elif avg <= 35:
            return 75
        elif avg <= 45:
            return 60
        elif avg <= 55:
            return 50
        elif avg <= 65:
            return 40
        elif avg <= 75:
            return 25
        elif avg <= 85:
            return 10
        else:
            return 0

    # ── RSI ─────────────────────────────────────
    def _calculate_rsi(self, closes: np.ndarray, period: int = 14) -> Optional[float]:
        if len(closes) < period + 1:
            return None
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 2)

    @staticmethod
    def _score_rsi(rsi: Optional[float]) -> float:
        if rsi is None:
            return 50
        if rsi <= 20:
            return 100
        elif rsi <= 30:
            return 85
        elif rsi <= 40:
            return 70
        elif rsi <= 50:
            return 55
        elif rsi <= 60:
            return 45
        elif rsi <= 70:
            return 30
        elif rsi <= 80:
            return 15
        else:
            return 0

    # ── MA Bias ─────────────────────────────────
    def _score_ma_bias(self, closes: np.ndarray) -> tuple:
        if len(closes) < 60:
            return 50, {'ma20': None, 'ma60': None, 'bias20': None, 'bias60': None}
        try:
            ma20 = float(np.mean(closes[-20:]))
            ma60 = float(np.mean(closes[-60:]))
            price = float(closes[-1])
            if not (np.isfinite(ma20) and np.isfinite(ma60) and np.isfinite(price)):
                return 50, {'ma20': None, 'ma60': None, 'bias20': None, 'bias60': None}
            bias20 = (price - ma20) / ma20 * 100
            bias60 = (price - ma60) / ma60 * 100
        except Exception:
            return 50, {'ma20': None, 'ma60': None, 'bias20': None, 'bias60': None}

        # Combined score: deep negative bias = buy opportunity
        combined = bias60 * 0.6 + bias20 * 0.4
        if combined <= -15:
            score = 100
        elif combined <= -10:
            score = 85
        elif combined <= -5:
            score = 70
        elif combined <= 0:
            score = 55
        elif combined <= 5:
            score = 45
        elif combined <= 10:
            score = 30
        elif combined <= 15:
            score = 15
        else:
            score = 0
        return score, {'ma20': round(ma20, 2), 'ma60': round(ma60, 2),
                       'bias20': round(bias20, 2), 'bias60': round(bias60, 2)}

    # ── MACD ────────────────────────────────────
    def _score_macd(self, closes: np.ndarray) -> tuple:
        if len(closes) < 35:
            return 50, {'macd_hist': None, 'macd_hist_prev': None, 'trend': None}

        try:
            ema12 = self._ema(closes, 12)
            ema26 = self._ema(closes, 26)
            dif = ema12 - ema26
            dea = self._ema(dif, 9)
            hist = dif - dea

            hist_current = float(hist[-1])
            hist_prev = float(hist[-2]) if len(hist) >= 2 else hist_current

            if not (np.isfinite(hist_current) and np.isfinite(hist_prev)):
                return 50, {'macd_hist': None, 'macd_hist_prev': None, 'trend': None}
        except Exception:
            return 50, {'macd_hist': None, 'macd_hist_prev': None, 'trend': None}

        # Bullish: hist positive and increasing, or turning from negative to positive
        if hist_current > 0 and hist_current > hist_prev:
            score = 85
        elif hist_current > 0:
            score = 70
        elif hist_current > hist_prev and hist_prev < 0:
            score = 90  # Golden cross signal
        elif hist_current > hist_prev:
            score = 60
        elif hist_current < hist_prev and hist_current < 0:
            score = 10
        elif hist_current < 0:
            score = 25
        else:
            score = 50

        return score, {'macd_hist': round(hist_current, 4),
                       'macd_hist_prev': round(hist_prev, 4),
                       'trend': 'bullish' if hist_current > 0 else 'bearish'}

    @staticmethod
    def _ema(arr: np.ndarray, period: int) -> np.ndarray:
        """Calculate EMA"""
        if len(arr) < period:
            return np.full(len(arr), arr[-1])
        alpha = 2 / (period + 1)
        ema = np.zeros_like(arr, dtype=float)
        ema[0] = arr[0]
        for i in range(1, len(arr)):
            ema[i] = alpha * arr[i] + (1 - alpha) * ema[i - 1]
        return ema

    # ── Volume-Price ────────────────────────────
    def _score_volume_price(self, opens: np.ndarray, highs: np.ndarray,
                            lows: np.ndarray, closes: np.ndarray,
                            volumes: np.ndarray) -> tuple:
        if len(volumes) < 20:
            return 50, {'volume_ratio': None, 'price_change': None}

        vol_avg = float(np.mean(volumes[-20:]))
        vol_today = float(volumes[-1])
        volume_ratio = vol_today / vol_avg if vol_avg > 0 else 1.0

        price_change = (closes[-1] - opens[-1]) / opens[-1] * 100 if opens[-1] > 0 else 0

        # Bottom accumulation: high volume + positive price change
        if volume_ratio > 2.0 and price_change > 3:
            score = 95
        elif volume_ratio > 1.5 and price_change > 2:
            score = 80
        elif volume_ratio > 1.5 and price_change > 0:
            score = 65
        elif volume_ratio > 1.5 and price_change < -2:
            score = 10  # Distribution
        elif volume_ratio < 0.5 and abs(price_change) < 1:
            score = 50  # Quiet
        elif price_change > 3:
            score = 70
        elif price_change < -3:
            score = 20
        else:
            score = 50

        return score, {'volume_ratio': round(volume_ratio, 2),
                       'price_change': round(price_change, 2)}

    # ── Trend ───────────────────────────────────
    def _score_trend(self, closes: np.ndarray, volumes: np.ndarray) -> tuple:
        if len(closes) < 20:
            return 50, {'slope_20d': None, 'volatility': None, 'trend_dir': None}

        try:
            # Linear regression slope over last 20 days
            x = np.arange(len(closes[-20:]))
            y = closes[-20:]
            if not np.all(np.isfinite(y)):
                return 50, {'slope_20d': None, 'volatility': None, 'trend_dir': None}
            slope = np.polyfit(x, y, 1)[0]
            slope_pct = slope / y[0] * 100  # slope as % of starting price

            # Volatility (ATR-like)
            if len(closes) >= 20:
                daily_range = np.array([
                    max(closes[i], closes[i - 1]) - min(closes[i], closes[i - 1])
                    for i in range(-19, 0)
                ])
                vol = np.mean(daily_range)
                base = np.mean(closes[-20:])
                if vol > 0 and base > 0 and np.isfinite(vol) and np.isfinite(base):
                    volatility = float(vol / base * 100)
                else:
                    volatility = 2.0
            else:
                volatility = 2.0
        except Exception:
            return 50, {'slope_20d': None, 'volatility': None, 'trend_dir': None}

        # Score: strong uptrend at low volatility = hold; downtrend = potential buy if steep
        if slope_pct > 3 and volatility < 3:
            score = 70  # Steady uptrend, not cheap but strong
        elif slope_pct > 1:
            score = 55
        elif slope_pct > -1:
            score = 50
        elif slope_pct > -3:
            score = 40  # Mild downtrend
        elif slope_pct > -5:
            score = 60  # Steep downtrend = possible reversal zone
        else:
            score = 75  # Very steep drop = panic bottom potential

        trend_dir = 'up' if slope_pct > 1 else 'down' if slope_pct < -1 else 'flat'
        return score, {'slope_20d': round(slope_pct, 3),
                       'volatility': round(volatility, 2),
                       'trend_dir': trend_dir}

    # ── Bollinger Bands ─────────────────────────
    @staticmethod
    def _calc_bollinger(closes: np.ndarray, period: int = 20, num_std: float = 2.0) -> Dict:
        """
        20-period Bollinger Bands (2 standard deviations, the standard
        default). percent_b expresses where the latest close sits relative
        to the bands: 0 = sitting on the lower band, 1 = sitting on the
        upper band, <0 / >1 = price has pierced through the band.
        """
        if len(closes) < period:
            return {'bb_upper': None, 'bb_mid': None, 'bb_lower': None, 'percent_b': None}
        try:
            window = closes[-period:]
            mid = float(np.mean(window))
            std = float(np.std(window))
            if not (np.isfinite(mid) and np.isfinite(std)):
                return {'bb_upper': None, 'bb_mid': None, 'bb_lower': None, 'percent_b': None}
            upper = mid + num_std * std
            lower = mid - num_std * std
            price = float(closes[-1])
            band_width = upper - lower
            percent_b = (price - lower) / band_width if band_width > 0 else None
        except Exception:
            return {'bb_upper': None, 'bb_mid': None, 'bb_lower': None, 'percent_b': None}

        return {
            'bb_upper': round(upper, 2),
            'bb_mid': round(mid, 2),
            'bb_lower': round(lower, 2),
            'percent_b': round(percent_b, 3) if percent_b is not None else None,
        }

    # ── Recommendation ──────────────────────────
    @staticmethod
    def _recommendation(total: float) -> str:
        if total >= 90:
            return '強烈加碼'
        elif total >= 70:
            return '加碼買進'
        elif total >= 50:
            return '持有觀望'
        elif total >= 30:
            return '減碼獲利'
        else:
            return '出清避險'
