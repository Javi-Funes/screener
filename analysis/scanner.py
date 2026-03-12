import pandas as pd
import numpy as np
from typing import Optional, Dict
from config import settings
from data.fetcher import DataFetcher
from indicators import smc
from utils.logger import get_logger

logger = get_logger(__name__)

class SMCScanner:
    def __init__(self, fetcher: DataFetcher):
        self.fetcher = fetcher
        # Sector ETFs mapping (podría venir de config)
        self.sector_etf = {
            'Technology': 'XLK',
            'Financial Services': 'XLF',
            'Healthcare': 'XLV',
            'Energy': 'XLE',
            'Consumer Cyclical': 'XLY',
            'Consumer Defensive': 'XLP',
            'Industrials': 'XLI',
            'Basic Materials': 'XLB',
            'Communication Services': 'XLC',
        }

    def get_sector(self, ticker: str) -> str:
        """Obtiene sector de un ticker usando yfinance (con caché)."""
        # Podríamos implementar un caché simple
        try:
            info = yf.Ticker(ticker).info
            return info.get('sector', 'Unknown')
        except:
            return 'Unknown'

    def analyze(self, ticker: str, es_byma: bool = False) -> Optional[Dict]:
        """Analiza un ticker y devuelve dict con resultados si pasa filtros."""
        df = self.fetcher.fetch_ticker_data(ticker)
        if df is None:
            return None
        # Extraer arrays
        high = smc.to_arr(df['High'])
        low = smc.to_arr(df['Low'])
        close = smc.to_arr(df['Close'])
        volume = smc.to_arr(df['Volume'])
        price = float(close[-1])

        # Swings
        sh, sl = smc.find_swings(high, low, settings.SWING_LENGTH)
        if not sh or not sl:
            return None

        # Zonas
        top = max(val for _, val in sh[-5:])
        bottom = min(val for _, val in sl[-5:])
        if top == bottom:
            return None
        zones = smc.get_zones(top, bottom)
        rango = top - bottom
        pct_rango = (price - bottom) / rango * 100

        in_disc = zones['discount'][0] <= price <= zones['discount'][1]
        in_near = zones['near_discount'][0] <= price <= zones['near_discount'][1]
        if not (in_disc or in_near):
            return None
        zona = 'Discount' if in_disc else 'Near Discount'

        # Estructura
        estructura = smc.get_estructura(sh, sl)
        if settings.ESTRUCTURA_ALCISTA and estructura not in ['Alcista', 'Alcista Debil']:
            return None

        # Order Block
        ob_enc, ob_lvl = smc.detect_ob_encima(high, low, close, price, sh)

        # FVGs
        fvgs_all = smc.detect_fvg_all(high, low, close, price)
        fvg_bull = any(f['tipo'] == 'BULLISH' for f in fvgs_all)

        # Fibonacci
        fib_retrocesos, fib_ext = smc.calc_fibonacci_pois(sh, sl, price)

        # Absorción
        abs_hit, abs_vol = smc.detect_absorcion(volume, close, high, low)

        # Squeeze
        sq_hit = smc.detect_squeeze(high, low)

        # Relative Strength (solo para no BYMA)
        rs_hit = False
        rs_ratio = None
        if not es_byma:
            sector = self.get_sector(ticker)
            etf_sym = self.sector_etf.get(sector)
            if etf_sym and etf_sym in self.fetcher.ref_data:
                etf_df = self.fetcher.ref_data[etf_sym]
                spy_df = self.fetcher.ref_data.get('SPY')
                if spy_df is not None:
                    etf_close = smc.to_arr(etf_df['Close'])
                    spy_close = smc.to_arr(spy_df['Close'])
                    min_len = min(len(close), len(etf_close), len(spy_close))
                    if min_len > settings.RS_DIAS + 1:
                        ret_t = close[-1] / close[-settings.RS_DIAS] - 1
                        ret_etf = etf_close[-1] / etf_close[-settings.RS_DIAS] - 1
                        ret_spy = spy_close[-1] / spy_close[-settings.RS_DIAS] - 1
                        rs_vs_etf = (1 + ret_t) / (1 + ret_etf) if (1 + ret_etf) != 0 else 0
                        rs_etf_spy = (1 + ret_etf) / (1 + ret_spy) if (1 + ret_spy) != 0 else 0
                        rs_hit = rs_vs_etf >= settings.RS_RATIO_MIN and rs_etf_spy >= 0.99
                        rs_ratio = round(rs_vs_etf, 3)
        else:
            sector = 'Argentina'

        # RSI
        rsi = round(float(smc.calculate_rsi(pd.Series(close))[-1]), 1)

        # Volumen relativo
        avg_vol = float(np.mean(volume[-21:-1]))
        vol_ratio = round(float(volume[-1]) / avg_vol, 2) if avg_vol > 0 else 0

        # Score
        score = 2  # base por estar en zona
        if fvg_bull:
            score += 1
        if rs_hit:
            score += 1
        if abs_hit:
            score += 1
        if sq_hit:
            score += 1
        if ob_enc:
            score -= 1
        if score < settings.SCORE_MINIMO:
            return None

        # Construir resultado
        equil = (top + bottom) / 2
        result = {
            'ticker': ticker,
            'sector': sector,
            'score': score,
            'zona': zona,
            'pct_rango': round(pct_rango, 1),
            'estructura': estructura,
            'precio': round(price, 2),
            'swing_high': round(top, 2),
            'swing_low': round(bottom, 2),
            'equilibrium': round(equil, 2),
            'dist_equil': round((equil - price) / price * 100, 2),
            'ob_encima': f'SI ({ob_lvl})' if ob_enc else 'NO',
            'ob_enc_bool': ob_enc,
            'fvg': 'BULLISH' if fvg_bull else ('BEARISH' if fvgs_all else 'None'),
            'fvgs_all': fvgs_all,
            'fib_retrocesos': fib_retrocesos,
            'fib_extensiones': fib_ext,
            'rs_ratio': rs_ratio or '-',
            'rsi': rsi,
            'vol_ratio': vol_ratio,
            'abs_vol': abs_vol or '-',
            'squeeze': 'SI' if sq_hit else 'NO',
            'senales': f"{zona} | {estructura}",
            'target': round(price * (1 + settings.TARGET_PCT/100), 2),
            'stop': round(price * (1 - settings.STOP_PCT/100), 2),
            'tv_link': f'https://www.tradingview.com/chart/?symbol={ticker}',
        }
        return result
