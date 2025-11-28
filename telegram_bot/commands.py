from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from bot.trader import Trader

class TelegramCommands:
    def __init__(self, trader: Trader):
        self.trader = trader

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /status command handler
        """
        price = self.trader.exchange.get_ticker(self.trader.symbol)['last']
        position = self.trader.position
        
        msg = f"**Status Report**\n\nSymbol: {self.trader.symbol}\nCurrent Price: {price}\n"
        
        if position:
            pnl_pct = (price - position['entry_price']) / position['entry_price'] * 100
            if position['type'] == 'sell':
                pnl_pct = -pnl_pct
                
            msg += (
                f"\n**Open Position**:\n"
                f"Type: {position['type'].upper()}\n"
                f"Entry: {position['entry_price']}\n"
                f"PnL: {pnl_pct:.2f}%\n"
                f"SL: {position['sl']}\n"
                f"TP: {position['tp']}"
            )
        else:
            msg += "\nNo open positions."
            
        await update.message.reply_text(msg)

    async def balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # For paper trading, this might be mock data
        await update.message.reply_text("Balance check not implemented for paper trading yet.")

    def get_handlers(self):
        return [
            CommandHandler("status", self.status),
            CommandHandler("balance", self.balance)
        ]
