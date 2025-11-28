"""
Backtesting Module for Bitcoin Trading Bot

This module allows you to test the trading strategy against historical
data to evaluate performance before risking real money.

Usage:
    python -m bot.backtester --days 60
"""

import sys
import pandas as pd
import logging
from datetime import datetime, timedelta
from bot.exchange import ExchangeInterface
from bot.strategy import Strategy
from config.settings import Config

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class Backtester:
    def __init__(self, days=60):
        self.exchange = ExchangeInterface()
        self.strategy = Strategy()
        self.symbol = Config.SYMBOL
        self.timeframe = Config.TIMEFRAME
        self.days = days
        
        self.stop_loss_pct = Config.STOP_LOSS_PCT
        self.take_profit_pct = Config.TAKE_PROFIT_PCT
        
        # Results tracking
        self.trades = []
        self.equity_curve = []
        self.initial_capital = 10000  # USD
        self.capital = self.initial_capital
        self.position = None
        
    def fetch_historical_data(self):
        """Fetch historical OHLCV data"""
        logger.info(f"Fetching {self.days} days of {self.timeframe} data for {self.symbol}")
        
        # Calculate how many candles we need
        # For 15m: 96 candles per day
        # For 1h: 24 candles per day
        if self.timeframe == '15m':
            candles_per_day = 96
        elif self.timeframe == '1h':
            candles_per_day = 24
        elif self.timeframe == '5m':
            candles_per_day = 288
        else:  # 1m
            candles_per_day = 1440
        
        limit = self.days * candles_per_day
        
        # Fetch data
        df = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=min(limit, 1000))
        
        if df.empty:
            logger.error("Failed to fetch historical data")
            return None
        
        logger.info(f"Fetched {len(df)} candles from {df.iloc[0]['timestamp']} to {df.iloc[-1]['timestamp']}")
        return df
    
    def simulate_trade(self, signal, price, timestamp, analysis):
        """Simulate a trade based on signal"""
        
        if signal == 'buy' and self.position is None:
            # Open long position
            amount_usd = self.capital * 0.95  # Use 95% of capital
            amount_btc = amount_usd / price
            sl_price = price * (1 - self.stop_loss_pct)
            tp_price = price * (1 + self.take_profit_pct)
            
            self.position = {
                'type': 'long',
                'entry_price': price,
                'entry_time': timestamp,
                'amount_btc': amount_btc,
                'amount_usd': amount_usd,
                'sl': sl_price,
                'tp': tp_price,
                'reason': analysis.get('reason', '')
            }
            
            logger.info(f"[BUY] {timestamp} @ ${price:,.2f} | SL: ${sl_price:,.2f} | TP: ${tp_price:,.2f}")
            logger.info(f"      Reason: {analysis.get('reason', 'N/A')}")
        
        elif signal == 'sell' and self.position is not None:
            # Close position
            pnl_usd = (price - self.position['entry_price']) * self.position['amount_btc']
            pnl_pct = ((price - self.position['entry_price']) / self.position['entry_price']) * 100
            
            self.capital += pnl_usd
            
            trade = {
                'entry_time': self.position['entry_time'],
                'exit_time': timestamp,
                'entry_price': self.position['entry_price'],
                'exit_price': price,
                'pnl_usd': pnl_usd,
                'pnl_pct': pnl_pct,
                'exit_reason': 'signal',
                'reason': analysis.get('reason', '')
            }
            
            self.trades.append(trade)
            
            emoji = "🟢" if pnl_usd > 0 else "🔴"
            logger.info(f"[SELL] {timestamp} @ ${price:,.2f} | PnL: ${pnl_usd:+,.2f} ({pnl_pct:+.2f}%) {emoji}")
            logger.info(f"       Reason: {analysis.get('reason', 'N/A')}")
            
            self.position = None
    
    def check_stop_loss_take_profit(self, row):
        """Check if SL or TP was hit"""
        if self.position is None:
            return
        
        price_high = row['high']
        price_low = row['low']
        timestamp = row['timestamp']
        
        # Check Stop Loss
        if price_low <= self.position['sl']:
            exit_price = self.position['sl']
            pnl_usd = (exit_price - self.position['entry_price']) * self.position['amount_btc']
            pnl_pct = ((exit_price - self.position['entry_price']) / self.position['entry_price']) * 100
            
            self.capital += pnl_usd
            
            trade = {
                'entry_time': self.position['entry_time'],
                'exit_time': timestamp,
                'entry_price': self.position['entry_price'],
                'exit_price': exit_price,
                'pnl_usd': pnl_usd,
                'pnl_pct': pnl_pct,
                'exit_reason': 'stop_loss'
            }
            
            self.trades.append(trade)
            logger.info(f"[STOP LOSS] {timestamp} @ ${exit_price:,.2f} | PnL: ${pnl_usd:+,.2f} ({pnl_pct:+.2f}%) 🔴")
            
            self.position = None
        
        # Check Take Profit
        elif price_high >= self.position['tp']:
            exit_price = self.position['tp']
            pnl_usd = (exit_price - self.position['entry_price']) * self.position['amount_btc']
            pnl_pct = ((exit_price - self.position['entry_price']) / self.position['entry_price']) * 100
            
            self.capital += pnl_usd
            
            trade = {
                'entry_time': self.position['entry_time'],
                'exit_time': timestamp,
                'entry_price': self.position['entry_price'],
                'exit_price': exit_price,
                'pnl_usd': pnl_usd,
                'pnl_pct': pnl_pct,
                'exit_reason': 'take_profit'
            }
            
            self.trades.append(trade)
            logger.info(f"[TAKE PROFIT] {timestamp} @ ${exit_price:,.2f} | PnL: ${pnl_usd:+,.2f} ({pnl_pct:+.2f}%) 🟢")
            
            self.position = None
    
    def run_backtest(self):
        """Run the backtest"""
        logger.info("="*60)
        logger.info("STARTING BACKTEST")
        logger.info("="*60)
        
        # Fetch historical data
        df = self.fetch_historical_data()
        if df is None:
            return
        
        # Simulate trading
        logger.info("\nSimulating trades...\n")
        
        for i in range(200, len(df)):  # Start after EMA200 warmup
            # Get window of data for analysis
            window = df.iloc[max(0, i-100):i+1].copy()
            
            # Run strategy analysis
            analysis = self.strategy.analyze(window)
            
            current_row = df.iloc[i]
            price = current_row['close']
            timestamp = current_row['timestamp']
            
            # Check SL/TP first
            self.check_stop_loss_take_profit(current_row)
            
            # Process signal
            signal = analysis.get('signal')
            if signal:
                self.simulate_trade(signal, price, timestamp, analysis)
            
            # Track equity
            current_equity = self.capital
            if self.position:
                current_equity += (price - self.position['entry_price']) * self.position['amount_btc']
            
            self.equity_curve.append({
                'timestamp': timestamp,
                'equity': current_equity
            })
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate backtest performance report"""
        logger.info("\n" + "="*60)
        logger.info("BACKTEST RESULTS")
        logger.info("="*60)
        
        if not self.trades:
            logger.info("No trades executed during backtest period")
            return
        
        # Basic stats
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['pnl_usd'] > 0]        
        losing_trades = [t for t in self.trades if t['pnl_usd'] <= 0]
        
        win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0
        
        total_pnl = sum(t['pnl_usd'] for t in self.trades)
        avg_win = sum(t['pnl_usd'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t['pnl_usd'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        profit_factor = abs(sum(t['pnl_usd'] for t in winning_trades) / sum(t['pnl_usd'] for t in losing_trades)) if losing_trades and sum(t['pnl_usd'] for t in losing_trades) != 0 else float('inf')
        
        final_capital = self.capital
        total_return_pct = ((final_capital - self.initial_capital) / self.initial_capital) * 100
        
        # Print report
        logger.info(f"\n📊 Performance Metrics:")
        logger.info(f"   Total Trades: {total_trades}")
        logger.info(f"   Winning Trades: {len(winning_trades)} ({win_rate:.1f}%)")
        logger.info(f"   Losing Trades: {len(losing_trades)}")
        logger.info(f"\n💰 Profit & Loss:")
        logger.info(f"   Initial Capital: ${self.initial_capital:,.2f}")
        logger.info(f"   Final Capital: ${final_capital:,.2f}")
        logger.info(f"   Total PnL: ${total_pnl:+,.2f}")
        logger.info(f"   Total Return: {total_return_pct:+.2f}%")
        logger.info(f"\n📈 Trade Statistics:")
        logger.info(f"   Average Win: ${avg_win:,.2f}")
        logger.info(f"   Average Loss: ${avg_loss:,.2f}")
        logger.info(f"   Profit Factor: {profit_factor:.2f}")
        
        # Exit reasons
        sl_exits = len([t for t in self.trades if t['exit_reason'] == 'stop_loss'])
        tp_exits = len([t for t in self.trades if t['exit_reason'] == 'take_profit'])
        signal_exits = len([t for t in self.trades if t['exit_reason'] == 'signal'])
        
        logger.info(f"\n🚪 Exit Breakdown:")
        logger.info(f"   Stop Loss: {sl_exits}")
        logger.info(f"   Take Profit: {tp_exits}")
        logger.info(f"   Signal: {signal_exits}")
        
        # Assessment
        logger.info(f"\n✅ Assessment:")
        if win_rate >= 50 and profit_factor >= 1.5:
            logger.info("   🟢 GOOD - Strategy shows promise!")
        elif win_rate >= 40 and profit_factor >= 1.2:
            logger.info("   🟡 ACCEPTABLE - Consider optimization")
        else:
            logger.info("   🔴 POOR - Strategy needs significant improvement")
        
        logger.info("\n" + "="*60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Backtest Bitcoin Trading Strategy')
    parser.add_argument('--days', type=int, default=60, help='Number of days to backtest (default: 60)')
    
    args = parser.parse_args()
    
    backtester = Backtester(days=args.days)
    backtester.run_backtest()
