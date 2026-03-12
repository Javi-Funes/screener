import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Rutas
RATIOS_JSON_PATH = os.getenv("RATIOS_JSON_PATH", "results/ratios_cedears.json")
RESULTS_DIR = os.getenv("RESULTS_DIR", "results")

# Parámetros de trading (pueden sobreescribirse con variables de entorno)
SWING_LENGTH = int(os.getenv("SWING_LENGTH", 50))
DISCOUNT_PCT = float(os.getenv("DISCOUNT_PCT", 0.25))
NEAR_DISCOUNT_PCT = float(os.getenv("NEAR_DISCOUNT_PCT", 0.40))
EQUILIBRIUM_BAND = float(os.getenv("EQUILIBRIUM_BAND", 0.05))
ESTRUCTURA_ALCISTA = os.getenv("ESTRUCTURA_ALCISTA", "True").lower() == "true"
RS_DIAS = int(os.getenv("RS_DIAS", 5))
RS_RATIO_MIN = float(os.getenv("RS_RATIO_MIN", 1.02))
ABSORCION_VOL_RATIO = float(os.getenv("ABSORCION_VOL_RATIO", 2.5))
SQUEEZE_RATIO = float(os.getenv("SQUEEZE_RATIO", 0.65))
SCORE_MINIMO = int(os.getenv("SCORE_MINIMO", 3))
TARGET_PCT = float(os.getenv("TARGET_PCT", 3.0))
STOP_PCT = float(os.getenv("STOP_PCT", 1.5))
DATA_PERIOD = os.getenv("DATA_PERIOD", "1y")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 10))
SLEEP_BETWEEN = float(os.getenv("SLEEP_BETWEEN", 1.5))
CCL_FALLBACK = float(os.getenv("CCL_FALLBACK", 1200.0))

# Universos (se pueden pasar por JSON externo, pero por ahora los dejamos fijos)
# (Podrían moverse a un archivo de configuración si se desea)
