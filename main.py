import asyncio
import logging
import uvicorn
from telegram.ext import ApplicationBuilder
from config.settings import Config
from bot.trader import Trader
from telegram_bot.notifier import TelegramNotifier
from telegram_bot.commands import TelegramCommands
from api.server import app, set_trader

# Configure Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def trading_loop(trader: Trader, notifier: TelegramNotifier):
    logger.info("Starting trading loop...")
    while True:
        try:
            logger.info("Running analysis...")
            result = trader.run_analysis()
            
            if result:
                # Send signal via Telegram
                await notifier.send_signal(result)
                
        except Exception as e:
            logger.error(f"Error in trading loop: {e}")
        
        # Wait for next candle (e.g., 60 seconds)
        await asyncio.sleep(60)

async def main():
    # Initialize Components
    trader = Trader()
    notifier = TelegramNotifier()
    
    # Inject trader into API
    set_trader(trader)
    
    # Initialize Telegram Bot Application (for commands)
    if Config.TELEGRAM_BOT_TOKEN:
        telegram_app = ApplicationBuilder().token(Config.TELEGRAM_BOT_TOKEN).build()
        commands = TelegramCommands(trader)
        for handler in commands.get_handlers():
            telegram_app.add_handler(handler)
        
        # Start Telegram polling in background
        await telegram_app.initialize()
        await telegram_app.start()
        await telegram_app.updater.start_polling()
        logger.info("Telegram bot started.")
        
        # Send Welcome Message
        await notifier.send_message("🚀 **Bitcoin Bot Started!**\n\nMonitoring BTC/USDT market...\nAccess Dashboard: http://localhost:8000")
    
    # Start API Server
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    
    # Run everything
    try:
        await asyncio.gather(
            server.serve(),
            trading_loop(trader, notifier)
        )
    except KeyboardInterrupt:
        logger.info("Stopping bot...")
    finally:
        if Config.TELEGRAM_BOT_TOKEN:
            await telegram_app.updater.stop()
            await telegram_app.stop()
            await telegram_app.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
