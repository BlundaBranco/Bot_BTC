import logging
from bot.exchange import ExchangeInterface
from bot.strategy import Strategy
from bot.storage import Storage  # <--- Importamos la DB
from config.settings import Config

logger = logging.getLogger(__name__)

class Trader:
    def __init__(self):
        self.exchange = ExchangeInterface()
        self.strategy = Strategy()
        self.storage = Storage()  # <--- Iniciamos la DB
        
        self.symbol = Config.SYMBOL
        self.timeframe = Config.TIMEFRAME
        self.stop_loss_pct = Config.STOP_LOSS_PCT
        self.take_profit_pct = Config.TAKE_PROFIT_PCT
        
        # Cargar posición desde la DB al iniciar (Persistencia)
        self.position = self.storage.get_open_position(self.symbol)
        if self.position:
            logger.info(f"Resumed open position from DB: {self.position}")

    def run_analysis(self):
        df = self.exchange.fetch_ohlcv(self.symbol, self.timeframe)
        if df.empty:
            logger.warning("No data fetched")
            return None

        analysis = self.strategy.analyze(df)
        self.latest_analysis = analysis
        signal = analysis.get('signal')
        price = analysis.get('price')
        
        # Lógica de Trading
        if signal == 'buy' and not self.position:
            return self.open_position('buy', price)
            
        elif signal == 'sell' and self.position:
            return self.close_position(price)

        # Revisar Stop Loss / Take Profit si hay posición abierta
        if self.position:
            sl = self.position['sl']
            tp = self.position['tp']
            
            if price <= sl:
                logger.info(f"Stop Loss hit at {price}")
                return self.close_position(price, reason="Stop Loss")
            elif price >= tp:
                logger.info(f"Take Profit hit at {price}")
                return self.close_position(price, reason="Take Profit")

        return None

    def open_position(self, side, price):
        amount = 0.001 # Monto fijo demo
        sl = price * (1 - self.stop_loss_pct)
        tp = price * (1 + self.take_profit_pct)
        
        # Ejecutar en exchange (simulado o real)
        order = self.exchange.create_order(self.symbol, 'market', side, amount)
        
        if order:
            trade_data = {
                'symbol': self.symbol,
                'type': side,
                'entry_price': price,
                'amount': amount,
                'sl': sl,
                'tp': tp
            }
            # Guardar en Base de Datos y actualizar memoria
            trade_id = self.storage.save_trade(trade_data)
            self.position = trade_data
            self.position['id'] = trade_id # Guardamos el ID de la DB
            
            logger.info(f"Opened position: {self.position}")
            return {'action': 'buy', 'price': price, 'sl': sl, 'tp': tp}
        return None

    def close_position(self, price, reason="Signal"):
        if not self.position:
            return None
            
        amount = self.position['amount']
        # Vender para cerrar
        order = self.exchange.create_order(self.symbol, 'market', 'sell', amount)
        
        if order:
            # Actualizar en DB
            if 'id' in self.position:
                self.storage.close_trade(self.position['id'], price)
            
            logger.info(f"Closed position at {price} ({reason})")
            old_position = self.position
            self.position = None
            return {'action': 'sell', 'price': price, 'reason': reason}
        return None