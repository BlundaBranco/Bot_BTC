import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """
    Configuración centralizada del Bot de Trading de Bitcoin
    
    Este archivo gestiona todos los parámetros del sistema:
    - Credenciales de API (Binance, Telegram)
    - Parámetros de estrategia de trading
    - Indicadores técnicos
    - Gestión de riesgo
    """
    
    # ==========================================
    # CREDENCIALES Y CONFIGURACIÓN BÁSICA
    # ==========================================
    
    # API de Binance para ejecutar operaciones
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
    BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")
    
    # Bot de Telegram para notificaciones en tiempo real
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    # Configuración del mercado
    TIMEFRAME = os.getenv("TIMEFRAME", "1m")        # Temporalidad de velas (1m, 5m, 15m, 1h)
    SYMBOL = os.getenv("SYMBOL", "BTC/USDT")         # Par de trading
    RISK_LEVEL = os.getenv("RISK_LEVEL", "medium")   # Nivel de riesgo (low, medium, high)
    
    # Modo de operación (True = simulación, False = trading real)
    PAPER_TRADING = os.getenv("PAPER_TRADING", "True").lower() == "true"
    
    # ==========================================
    # ESTRATEGIA: SEGUIMIENTO DE TENDENCIAS
    # ==========================================
    
    # Medias Móviles Exponenciales (EMAs)
    EMA_TREND = 200    # Filtro de tendencia largo plazo (solo opera si precio > EMA 200)
    EMA_FAST = 20      # EMA rápida para señales de entrada (cruces y rebotes)
    EMA_SLOW = 50      # EMA lenta para soporte/resistencia dinámica
    
    # ==========================================
    # CONFIRMACIÓN DE VOLUMEN
    # ==========================================
    
    # El volumen debe confirmar el movimiento para evitar señales falsas
    VOLUME_PERIOD = 20         # Período para calcular volumen promedio
    VOLUME_MULTIPLIER = 0.5    # Volumen actual debe ser 1.5x el promedio
    
    # ==========================================
    # INDICADORES DE MOMENTUM
    # ==========================================
    
    # RSI (Relative Strength Index)
    RSI_PERIOD = 14    # Período de cálculo del RSI
    RSI_MIN = 40       # RSI mínimo para entrada (evita sobreventa extrema)
    RSI_MAX = 70       # RSI máximo para entrada (evita sobrecompra)
    RSI_EXIT = 75      # RSI extremo para salida anticipada
    
    # MACD (Moving Average Convergence Divergence)
    MACD_FAST = 12     # EMA rápida del MACD
    MACD_SLOW = 26     # EMA lenta del MACD
    MACD_SIGNAL = 9    # Línea de señal del MACD
    
    # ==========================================
    # GESTIÓN DE RIESGO
    # ==========================================
    
    # Ratios de Stop Loss y Take Profit
    STOP_LOSS_PCT = 0.02      # Stop Loss del 2% (protección de capital)
    TAKE_PROFIT_PCT = 0.05    # Take Profit del 5% (ratio riesgo/recompensa 1:2.5)
    
    # ==========================================
    # NOTAS IMPORTANTES
    # ==========================================
    """
    ESTRATEGIA DE ENTRADA (todas las condiciones deben cumplirse):
    1. Precio > EMA 200 (tendencia alcista confirmada)
    2. Precio cruza EMA 50 hacia arriba O rebota en EMA 20
    3. RSI entre 40-70 (momentum saludable)
    4. Volumen > 1.5x promedio (confirmación de movimiento)
    5. MACD con cruce alcista (convergencia positiva)
    
    ESTRATEGIA DE SALIDA (cualquiera activa la salida):
    - Precio cruza por debajo de EMA 50
    - RSI > 75 (sobrecompra extrema)
    - MACD con cruce bajista
    - Stop Loss alcanzado (-2%)
    - Take Profit alcanzado (+5%)
    
    FRECUENCIA ESPERADA:
    - Con temporalidad de 15 minutos: 1-3 señales por semana
    - Estrategia conservadora enfocada en calidad sobre cantidad
    
    RATIO RIESGO/RECOMPENSA:
    - 1:2.5 (arriesgas $1 para ganar $2.50)
    - Stop Loss ajustado: 2%
    - Take Profit objetivo: 5%
    """