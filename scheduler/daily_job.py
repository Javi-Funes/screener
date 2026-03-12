import schedule
import time
from datetime import datetime
from main import run_scan_and_generate_report
from bot.telegram_bot import SMCBot
from utils.logger import get_logger

logger = get_logger(__name__)

def job():
    logger.info("Ejecutando scan diario...")
    try:
        reporte = run_scan_and_generate_report()  # función que ejecuta el scan y guarda archivos
        # Enviar por Telegram
        bot = SMCBot()
        # (Necesitamos una instancia del bot con el token)
        # Podríamos usar una función separada para enviar
        asyncio.run(bot.send_daily_report())
    except Exception as e:
        logger.error(f"Error en job diario: {e}")

def run_scheduler():
    # Programar a las 7 AM Argentina (hora local del servidor)
    schedule.every().day.at("07:00").do(job)
    logger.info("Scheduler iniciado. Próxima ejecución a las 07:00.")
    while True:
        schedule.run_pending()
        time.sleep(60)
