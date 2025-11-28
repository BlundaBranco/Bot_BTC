import logging
from telegram import Bot
from config.settings import Config
import asyncio

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.bot = Bot(token=self.token) if self.token else None

    async def send_message(self, message: str):
        if not self.bot or not self.chat_id:
            logger.warning("Telegram token or chat_id not set. Cannot send message.")
            return

        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message)
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")

    async def send_signal(self, signal_data: dict):
        """
        Format and send a trading signal.
        signal_data: {'action': 'buy'/'sell', 'price': float, 'sl': float, 'tp': float}
        """
        action = signal_data.get('action').upper()
        price = signal_data.get('price')
        sl = signal_data.get('sl')
        tp = signal_data.get('tp')
        
        emoji = "🟢" if action == "BUY" else "🔴"
        
        message = (
            f"{emoji} **SIGNAL: {action}**\n\n"
            f"Symbol: {Config.SYMBOL}\n"
            f"Price: {price}\n"
            f"Stop Loss: {sl}\n"
            f"Take Profit: {tp}\n"
        )
        await self.send_message(message)
