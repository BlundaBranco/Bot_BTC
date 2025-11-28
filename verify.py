import logging
import pandas as pd
from bot.exchange import ExchangeInterface
from bot.strategy import Strategy

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_exchange():
    logger.info("Testing Exchange Connection...")
    exchange = ExchangeInterface()
    
    # Test Ticker
    ticker = exchange.get_ticker("BTC/USDT")
    if ticker:
        logger.info(f"Ticker BTC/USDT: {ticker['last']}")
    else:
        logger.error("Failed to fetch ticker.")

    # Test OHLCV
    logger.info("Testing OHLCV Fetch...")
    df = exchange.fetch_ohlcv("BTC/USDT", "1m", limit=50)
    if not df.empty:
        logger.info(f"Fetched {len(df)} candles.")
        logger.info(f"Last candle: {df.iloc[-1]['timestamp']} - {df.iloc[-1]['close']}")
        return df
    else:
        logger.error("Failed to fetch OHLCV.")
        return pd.DataFrame()

def test_strategy(df):
    logger.info("Testing Strategy Logic...")
    if df.empty:
        logger.warning("No data to test strategy.")
        return

    strategy = Strategy()
    analysis = strategy.analyze(df)
    logger.info(f"Strategy Analysis Result: {analysis}")

if __name__ == "__main__":
    df = test_exchange()
    test_strategy(df)
