from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import asyncio
from bot.trader import Trader
from config.settings import Config
import os

app = FastAPI()

# Directorios base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Montar archivos estáticos (CSS, JS, Favicon)
# Asegúrate de que tu style.css esté en api/static/style.css
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Configurar Templates (Jinja2)
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Referencia global al trader (se inyecta desde main.py)
bot_trader: Trader = None

def set_trader(trader: Trader):
    global bot_trader
    bot_trader = trader

@app.get("/api/status")
async def get_status():
    if not bot_trader:
        return {"status": "initializing"}
    
    # Obtenemos toda la info del ticker (máximos, mínimos, volumen)
    ticker = bot_trader.exchange.get_ticker(bot_trader.symbol)
    
    # Valores por defecto por si falla la conexión
    price = ticker['last'] if ticker else 0.0
    high_24h = ticker.get('high', 0.0)
    low_24h = ticker.get('low', 0.0)
    vol_24h = ticker.get('baseVolume', 0.0) # Volumen en BTC
    change_24h = ticker.get('percentage', 0.0)

    latest = getattr(bot_trader, 'latest_analysis', {})
    
    return {
        "status": "active",
        "symbol": bot_trader.symbol,
        "price": price,
        "timeframe": Config.TIMEFRAME,
        
        # --- NUEVA SECCIÓN DE ESTADÍSTICAS ---
        "market_stats": {
            "high": high_24h,
            "low": low_24h,
            "volume": vol_24h,
            "change": change_24h
        },
        # -------------------------------------

        "last_signal": latest.get('signal', None),
        "signal_reason": latest.get('reason', 'Esperando datos...'),
        "indicators": {
            "rsi": latest.get('rsi', 50.0),
            "macd": latest.get('macd', 0.0),
            "trend": latest.get('trend', 'neutral'),
            "volume_confirmed": latest.get('volume_confirmed', False),
            "volume_ratio": latest.get('volume_ratio', 1.0)
        }
    }


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    # Solo para testing individual, normalmente se corre desde main.py
    uvicorn.run(app, host="0.0.0.0", port=8000)