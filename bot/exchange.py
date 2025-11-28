import ccxt
import pandas as pd
from config.settings import Config
import logging

logger = logging.getLogger(__name__)

class ExchangeInterface:
    def __init__(self):
        # Usamos Binance por defecto, pero CCXT soporta cientos
        self.exchange_id = 'binance'
        self.exchange_class = getattr(ccxt, self.exchange_id)
        exchange_config = {
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
            },
        }
        
        # Si hay claves API reales, las usamos. Si no, modo lectura pública.
        if Config.BINANCE_API_KEY and Config.BINANCE_API_KEY != 'dummy_api_key':
            exchange_config['apiKey'] = Config.BINANCE_API_KEY
            exchange_config['secret'] = Config.BINANCE_SECRET_KEY
            
        self.exchange = self.exchange_class(exchange_config)
        self.paper_trading = Config.PAPER_TRADING

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 300) -> pd.DataFrame:
        """
        Fetch OHLCV data from the exchange.
        LIMIT UPDATED: 300 candles to support EMA200 strategy calculation immediately.
        """
        try:
            # Pedimos 300 velas para tener historial suficiente
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Ordenar por tiempo asegura que los indicadores se calculen bien
            df = df.sort_values('timestamp')
            
            return df
        except Exception as e:
            logger.error(f"Error fetching OHLCV: {e}")
            return pd.DataFrame()

    def get_ticker(self, symbol: str):
        try:
            return self.exchange.fetch_ticker(symbol)
        except Exception as e:
            logger.error(f"Error fetching ticker: {e}")
            return None

    def create_order(self, symbol: str, type: str, side: str, amount: float, price: float = None):
        """
        Executes an order. Checks for Paper Trading mode first.
        """
        if self.paper_trading:
            logger.info(f"PAPER TRADING: Executed {side} {amount} {symbol} at estimated {price}")
            # Simulamos una respuesta de orden exitosa
            return {
                'id': 'paper_trade_' + str(pd.Timestamp.now().timestamp()),
                'status': 'closed',
                'filled': amount,
                'price': price,
                'side': side
            }
        
        try:
            # Ejecución real en exchange (CUIDADO con dinero real)
            return self.exchange.create_order(symbol, type, side, amount, price)
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return None