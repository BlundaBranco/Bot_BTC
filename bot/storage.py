import sqlite3
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
DB_NAME = "trading_bot.db"

class Storage:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        # Tabla de Operaciones (Trades)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                type TEXT NOT NULL,  -- 'buy' o 'sell'
                entry_price REAL NOT NULL,
                amount REAL NOT NULL,
                stop_loss REAL,
                take_profit REAL,
                status TEXT DEFAULT 'open', -- 'open' o 'closed'
                entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                exit_time TIMESTAMP,
                exit_price REAL,
                pnl REAL
            )
        ''')
        self.conn.commit()

    def save_trade(self, trade_data):
        """Guarda una nueva operación abierta"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO trades (symbol, type, entry_price, amount, stop_loss, take_profit, status)
                VALUES (?, ?, ?, ?, ?, ?, 'open')
            ''', (
                trade_data['symbol'], trade_data['type'], trade_data['entry_price'],
                trade_data['amount'], trade_data['sl'], trade_data['tp']
            ))
            self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"DB Error saving trade: {e}")
            return None

    def get_open_position(self, symbol):
        """Busca si hay una operación abierta para este par"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM trades WHERE symbol = ? AND status = 'open'", (symbol,))
        row = cursor.fetchone()
        if row:
            # Convertimos la tupla de la DB a un diccionario útil
            return {
                'id': row[0], 'symbol': row[1], 'type': row[2],
                'entry_price': row[3], 'amount': row[4], 'sl': row[5], 'tp': row[6]
            }
        return None

    def close_trade(self, trade_id, exit_price):
        """Cierra una operación existente"""
        try:
            # Primero obtenemos el precio de entrada para calcular ganancia/pérdida
            cursor = self.conn.cursor()
            cursor.execute("SELECT entry_price, amount, type FROM trades WHERE id = ?", (trade_id,))
            row = cursor.fetchone()
            
            if not row: return
            
            entry_price, amount, side = row
            
            # Calculo simple de PnL (Profit and Loss)
            if side == 'buy':
                pnl = (exit_price - entry_price) * amount
            else:
                pnl = (entry_price - exit_price) * amount

            cursor.execute('''
                UPDATE trades 
                SET status = 'closed', exit_price = ?, exit_time = ?, pnl = ?
                WHERE id = ?
            ''', (exit_price, datetime.now(), pnl, trade_id))
            self.conn.commit()
            logger.info(f"Trade #{trade_id} closed in DB. PnL: {pnl}")
        except Exception as e:
            logger.error(f"DB Error closing trade: {e}")