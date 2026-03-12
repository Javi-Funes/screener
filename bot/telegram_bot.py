import asyncio
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import settings
from report.generator import generar_reporte
from analysis.scanner import SMCScanner
from data.fetcher import DataFetcher
from utils.logger import get_logger

logger = get_logger(__name__)

class SMCBot:
    def __init__(self):
        self.token = settings.TELEGRAM_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.fetcher = DataFetcher()
        self.scanner = SMCScanner(self.fetcher)
        self.app = Application.builder().token(self.token).build()
        self._register_handlers()

    def _register_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("report", self.report))
        self.app.add_handler(CommandHandler("help", self.help))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Bot SMC activo. Usa /report para obtener el último reporte.")

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Comandos:\n/report - Reporte completo\n/help - Esta ayuda")

    async def report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Generando reporte, por favor espera...")
        try:
            # Ejecutar scan completo (podría ser pesado, mejor usar el último guardado o generarlo bajo demanda)
            # Por simplicidad, leeremos el último reporte generado (results/reporte_latest.txt)
            import os
            latest_path = os.path.join(settings.RESULTS_DIR, 'reporte_latest.txt')
            if os.path.exists(latest_path):
                with open(latest_path, 'r', encoding='utf-8') as f:
                    reporte = f.read()
                await update.message.reply_text(reporte[:4000])  # Telegram max 4096
            else:
                await update.message.reply_text("No hay reporte generado aún. Espera la ejecución diaria.")
        except Exception as e:
            logger.error(f"Error enviando reporte: {e}")
            await update.message.reply_text("Error al obtener el reporte.")

    async def send_daily_report(self):
        """Envía el reporte diario automáticamente."""
        latest_path = os.path.join(settings.RESULTS_DIR, 'reporte_latest.txt')
        if os.path.exists(latest_path):
            with open(latest_path, 'r', encoding='utf-8') as f:
                reporte = f.read()
            # Dividir si es muy largo
            parts = [reporte[i:i+4000] for i in range(0, len(reporte), 4000)]
            for part in parts:
                await self.app.bot.send_message(chat_id=self.chat_id, text=part)
        else:
            await self.app.bot.send_message(chat_id=self.chat_id, text="No se pudo generar el reporte diario.")

    def run(self):
        """Inicia el bot en modo polling."""
        self.app.run_polling()
