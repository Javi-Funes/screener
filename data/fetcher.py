import yfinance as yf
import pandas as pd
import requests
import json
import os
import time
from typing import Optional, Dict
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class DataFetcher:
    def __init__(self):
        self.ccl_cache = None
        self.ccl_source = None
        self.ccl_timestamp = None
        self.ratios = self._load_ratios()
        self.ref_data = {}  # Para SPY y ETFs

    def _load_ratios(self) -> Dict[str, float]:
        """Carga ratios desde JSON, o retorna dict vacío si no existe."""
        if not os.path.exists(settings.RATIOS_JSON_PATH):
            logger.warning(f"Archivo de ratios no encontrado: {settings.RATIOS_JSON_PATH}")
            return {}
        with open(settings.RATIOS_JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Convertir a dict simple ticker -> ratio
        ratios = {}
        for ticker, info in data.items():
            if ticker == '_meta':
                continue
            ratio = info.get('ratio')
            if ratio:
                ratios[ticker] = float(ratio)
        logger.info(f"Ratios cargados: {len(ratios)} tickers")
        return ratios

    def get_ratio(self, ticker: str) -> float:
        """Retorna el ratio del ticker, o 1.0 si no está."""
        return self.ratios.get(ticker, 1.0)

    def fetch_ccl(self) -> tuple[float, str]:
        """Obtiene CCL con caché de 5 minutos."""
        if self.ccl_cache and (time.time() - self.ccl_timestamp) < 300:
            return self.ccl_cache, self.ccl_source
        # Lógica igual a la original
        try:
            r = requests.get('https://criptoya.com/api/dolar', timeout=5)
            if r.status_code == 200:
                data = r.json()
                ccl_data = data.get('ccl', {})
                venta = ccl_data.get('ask') or ccl_data.get('venta') or ccl_data.get('price')
                if venta and float(venta) > 100:
                    self.ccl_cache = float(venta)
                    self.ccl_source = 'CriptoYa'
                    self.ccl_timestamp = time.time()
                    return self.ccl_cache, self.ccl_source
        except Exception as e:
            logger.error(f"Error CriptoYa: {e}")
        try:
            r = requests.get('https://dolarapi.com/v1/dolares/contadoconliqui', timeout=5)
            if r.status_code == 200:
                data = r.json()
                venta = data.get('venta')
                if venta and float(venta) > 100:
                    self.ccl_cache = float(venta)
                    self.ccl_source = 'DolarAPI'
                    self.ccl_timestamp = time.time()
                    return self.ccl_cache, self.ccl_source
        except Exception as e:
            logger.error(f"Error DolarAPI: {e}")
        logger.warning("Usando CCL fallback")
        return settings.CCL_FALLBACK, 'FALLBACK'

    def fetch_ticker_data(self, ticker: str, period: str = None) -> Optional[pd.DataFrame]:
        """Descarga datos históricos de un ticker."""
        period = period or settings.DATA_PERIOD
        try:
            df = yf.download(ticker, period=period, interval='1d', progress=False, auto_adjust=True)
            if df is None or df.empty or len(df) < settings.SWING_LENGTH + 20:
                logger.debug(f"Datos insuficientes para {ticker}")
                return None
            return df.dropna()
        except Exception as e:
            logger.error(f"Error descargando {ticker}: {e}")
            return None

    def fetch_reference_data(self, symbols: list):
        """Descarga datos de referencia (SPY, ETFs) y los guarda en caché."""
        for sym in symbols:
            if sym not in self.ref_data:
                df = self.fetch_ticker_data(sym)
                if df is not None:
                    self.ref_data[sym] = df
        return self.ref_data
