import pandas as pd
import numpy as np
from config.settings import Config
import logging

logger = logging.getLogger(__name__)

class Strategy:
    """
    Professional Trend-Following Strategy
    
    Entry Conditions (ALL must be true):
    1. Trend Filter: Price > EMA200 (only long in uptrend)
    2. Entry Signal: Price crosses above EMA50 OR bounces off EMA20
    3. Momentum: RSI between 40-70 (not in extremes)
    4. Volume: Current volume > 1.5x average
    5. MACD: Bullish crossover confirmation
    
    Exit Conditions (ANY triggers exit):
    1. Price crosses below EMA50
    2. RSI > 75 (extreme overbought)
    3. MACD bearish crossover
    4. Stop Loss / Take Profit managed by Trader
    """
    
    def __init__(self):
        # Trend EMAs
        self.ema_trend = Config.EMA_TREND
        self.ema_fast = Config.EMA_FAST
        self.ema_slow = Config.EMA_SLOW
        
        # Volume
        self.volume_period = Config.VOLUME_PERIOD
        self.volume_multiplier = Config.VOLUME_MULTIPLIER
        
        # RSI
        self.rsi_period = Config.RSI_PERIOD
        self.rsi_min = Config.RSI_MIN
        self.rsi_max = Config.RSI_MAX
        self.rsi_exit = Config.RSI_EXIT
        
        # MACD
        self.macd_fast = Config.MACD_FAST
        self.macd_slow = Config.MACD_SLOW
        self.macd_signal = Config.MACD_SIGNAL

    def calculate_ema(self, series, period):
        """Calculate Exponential Moving Average"""
        return series.ewm(span=period, adjust=False).mean()

    def calculate_rsi(self, series, period):
        """Calculate Relative Strength Index"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_macd(self, series, fast, slow, signal):
        """Calculate MACD and Signal Line"""
        exp1 = series.ewm(span=fast, adjust=False).mean()
        exp2 = series.ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        return macd, signal_line

    def analyze(self, df: pd.DataFrame) -> dict:
        """
        Analyze the DataFrame and return a trading signal.
        
        Returns:
            dict: {
                'signal': 'buy'/'sell'/None,
                'price': current price,
                'rsi': RSI value,
                'macd': MACD value,
                'trend': 'uptrend'/'downtrend',
                'volume_confirmed': bool,
                'reason': explanation string
            }
        """
        # Require enough data for EMA200
        if df.empty or len(df) < max(self.ema_trend, self.macd_slow):
            logger.warning(f"Insufficient data: {len(df)} candles")
            return {'signal': None, 'reason': 'Insufficient data'}

        # Calculate all indicators
        df['ema_trend'] = self.calculate_ema(df['close'], self.ema_trend)
        df['ema_fast'] = self.calculate_ema(df['close'], self.ema_fast)
        df['ema_slow'] = self.calculate_ema(df['close'], self.ema_slow)
        df['rsi'] = self.calculate_rsi(df['close'], self.rsi_period)
        df['macd'], df['macd_signal'] = self.calculate_macd(
            df['close'], self.macd_fast, self.macd_slow, self.macd_signal
        )
        df['volume_avg'] = df['volume'].rolling(window=self.volume_period).mean()

        # Get current and previous values
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        price = last['close']
        ema_trend = last['ema_trend']
        ema_fast = last['ema_fast']
        ema_slow = last['ema_slow']
        rsi = last['rsi']
        macd = last['macd']
        macd_signal = last['macd_signal']
        volume = last['volume']
        volume_avg = last['volume_avg']
        
        prev_macd = prev['macd']
        prev_macd_signal = prev['macd_signal']
        prev_price = prev['close']
        prev_ema_slow = prev['ema_slow']

        # Determine trend
        trend = 'uptrend' if price > ema_trend else 'downtrend'
        
        # Volume confirmation
        volume_confirmed = volume > (volume_avg * self.volume_multiplier)
        
        # MACD crossovers
        macd_bullish_cross = prev_macd < prev_macd_signal and macd > macd_signal
        macd_bearish_cross = prev_macd > prev_macd_signal and macd < macd_signal
        
        # Price crosses EMA signals
        price_cross_above_ema50 = prev_price < prev_ema_slow and price > ema_slow
        price_bounce_ema20 = abs(price - ema_fast) / price < 0.005  # Within 0.5%
        
        signal = None
        reason = []
        
        # ===== BUY CONDITIONS =====
        if trend == 'uptrend':
            reason.append("✓ Uptrend")
            
            if self.rsi_min <= rsi <= self.rsi_max:
                reason.append(f"✓ RSI healthy ({rsi:.1f})")
                
                if macd_bullish_cross:
                    reason.append("✓ MACD bullish cross")
                    
                    if volume_confirmed:
                        reason.append(f"✓ Volume confirmed ({volume/volume_avg:.1f}x)")
                        
                        if price_cross_above_ema50 or price_bounce_ema20:
                            if price_cross_above_ema50:
                                reason.append("✓ Price crossed above EMA50")
                            else:
                                reason.append("✓ Price near EMA20")
                            
                            signal = 'buy'
                        else:
                            reason.append("✗ No EMA entry signal")
                    else:
                        reason.append(f"✗ Low volume ({volume/volume_avg:.1f}x)")
                else:
                    reason.append("✗ No MACD bullish cross")
            else:
                reason.append(f"✗ RSI out of range ({rsi:.1f})")
        else:
            reason.append("✗ Downtrend (price < EMA200)")
        
        # ===== SELL CONDITIONS =====
        # Exit if extreme overbought
        if rsi > self.rsi_exit:
            signal = 'sell'
            reason = [f"⚠️ Extreme overbought (RSI {rsi:.1f})"]
        
        # Exit on MACD bearish cross
        elif macd_bearish_cross:
            signal = 'sell'
            reason = ["⚠️ MACD bearish crossover"]
        
        # Exit if price crosses below EMA50
        elif prev_price > prev_ema_slow and price < ema_slow:
            signal = 'sell'
            reason = ["⚠️ Price crossed below EMA50"]

        return {
            'signal': signal,  # Aquí usa la variable calculada, NO 'buy' fijo
            'price': float(price),
            'rsi': float(rsi),
            'macd': float(macd),
            'trend': trend,
            'volume_confirmed': bool(volume_confirmed),
            'volume_ratio': float(volume / volume_avg) if volume_avg > 0 else 0,
            'ema_trend': float(ema_trend),
            'ema_slow': float(ema_slow),
            'ema_fast': float(ema_fast),
            'reason': ' | '.join(reason) if reason else 'Market Scanning...'
        }
