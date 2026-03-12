import sys
import os
from datetime import datetime
import pandas as pd

# Asegurar que podemos importar módulos internos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import settings
from data.fetcher import DataFetcher
from analysis.scanner import SMCScanner
from report.generator import generar_reporte
from utils.logger import setup_logger, get_logger

# Universos (podrían ir en config)
CEDEARS_NYSE = [
    'MELI', 'VIST', 'NU', 'MSFT', 'ORCL', 'HMY', 'SPY', 'USO', 'HUT', 'IBIT',
    'MU', 'NIO', 'NVDA', 'PBR', 'GOOGL', 'MSTR', 'AMZN', 'SQ', 'MO', 'KO',
    'AAPL', 'SATL', 'EWZ', 'SH', 'ASTS', 'TSLA', 'VXX', 'BRK-B', 'UNH', 'META',
    'ETHA', 'IBM', 'CRM', 'GLD', 'GLOB', 'COIN', 'QQQ', 'SLV', 'AMD', 'BAC',
    'V', 'URA', 'STNE', 'CSCO', 'ANF', 'XLE', 'PLTR', 'GOLD', 'MRNA', 'BITF',
    'PAGS', 'GPRK',
]

ADRS_ARG_NYSE = {
    'GGAL': {'byma': 'GGAL.BA',  'nombre': 'Grupo Galicia',   'ratio': 10},
    'YPF':  {'byma': 'YPFD.BA',  'nombre': 'YPF',             'ratio': 1},
    'PAM':  {'byma': 'PAMP.BA',  'nombre': 'Pampa Energia',   'ratio': 25},
    'BMA':  {'byma': 'BMA.BA',   'nombre': 'Banco Macro',     'ratio': 10},
    'CEPU': {'byma': 'CEPU.BA',  'nombre': 'Central Puerto',  'ratio': 10},
    'LOMA': {'byma': 'LOMA.BA',  'nombre': 'Loma Negra',      'ratio': 5},
    'SUPV': {'byma': 'SUPV.BA',  'nombre': 'Supervielle',     'ratio': 5},
    'TGS':  {'byma': 'TGSU2.BA', 'nombre': 'TGS',             'ratio': 5},
    'MELI': {'byma': 'MELI.BA',  'nombre': 'MercadoLibre',    'ratio': 1},
    'GLOB': {'byma': 'GLOB.BA',  'nombre': 'Globant',         'ratio': 1},
    'DESP': {'byma': 'DESP.BA',  'nombre': 'Despegar',        'ratio': 1},
}

PANEL_LIDER_BYMA = {
    'TXAR.BA':  'Ternium Argentina',
    'ALUA.BA':  'Aluar',
    'BBAR.BA':  'BBVA Argentina',
    'TECO2.BA': 'Telecom Argentina',
    'COME.BA':  'Sociedad Comercial del Plata',
    'CVH.BA':   'Cablevision Holding',
    'MIRG.BA':  'Mirgor',
    'BYMA.BA':  'BYMA',
    'VALO.BA':  'Grupo Valores',
    'EDN.BA':   'Edenor',
    'CRES.BA':  'Cresud',
}

logger = get_logger(__name__)

def run_scan_and_generate_report():
    """Ejecuta el scan completo, guarda archivos y retorna el reporte."""
    fetcher = DataFetcher()
    scanner = SMCScanner(fetcher)

    # 1. Obtener CCL
    ccl, fuente = fetcher.fetch_ccl()
    logger.info(f"CCL: {ccl} ({fuente})")

    # 2. Cargar referencias (SPY, ETFs)
    symbols_ref = ['SPY'] + list(scanner.sector_etf.values())
    fetcher.fetch_reference_data(symbols_ref)

    # 3. Rotación sectorial
    rotacion, spy_ret = get_rotation(fetcher, scanner)  # función auxiliar

    # 4. Escanear universos
    resultados_cedears = []
    for t in CEDEARS_NYSE:
        r = scanner.analyze(t, es_byma=False)
        if r:
            ratio = fetcher.get_ratio(t)
            r['ratio'] = ratio
            r['precio_ars'] = round((r['precio'] / ratio) * ccl, 0)
            r['stop_ars'] = round((r['stop'] / ratio) * ccl, 0)
            r['target_ars'] = round((r['target'] / ratio) * ccl, 0)
            resultados_cedears.append(r)
            logger.info(f"HIT {t}: score {r['score']}")
        # sleep entre batches

    resultados_adrs = []
    for t in ADRS_ARG_NYSE.keys():
        r = scanner.analyze(t, es_byma=False)
        if r:
            ratio = fetcher.get_ratio(t)
            r['ratio'] = ratio
            r['byma_local'] = ADRS_ARG_NYSE[t]['byma']
            r['precio_ars'] = round((r['precio'] / ratio) * ccl, 0)
            r['stop_ars'] = round((r['stop'] / ratio) * ccl, 0)
            r['target_ars'] = round((r['target'] / ratio) * ccl, 0)
            resultados_adrs.append(r)

    resultados_byma = []
    for t in PANEL_LIDER_BYMA.keys():
        r = scanner.analyze(t, es_byma=True)
        if r:
            r['ratio'] = 1
            r['precio_ars'] = r['precio']
            r['stop_ars'] = r['stop']
            r['target_ars'] = r['target']
            resultados_byma.append(r)

    # Ordenar
    for lst in [resultados_cedears, resultados_adrs, resultados_byma]:
        lst.sort(key=lambda x: (-x['score'], x['ob_enc_bool'], x['pct_rango']))

    # Generar reporte
    reporte = generar_reporte(ccl, fuente,
                              resultados_cedears,
                              resultados_adrs,
                              resultados_byma,
                              rotacion, spy_ret)

    # Guardar archivos
    os.makedirs(settings.RESULTS_DIR, exist_ok=True)
    date_str = datetime.now().strftime('%Y%m%d_%H%M')
    fname_dated = os.path.join(settings.RESULTS_DIR, f'reporte_{date_str}.txt')
    fname_latest = os.path.join(settings.RESULTS_DIR, 'reporte_latest.txt')
    with open(fname_dated, 'w', encoding='utf-8') as f:
        f.write(reporte)
    with open(fname_latest, 'w', encoding='utf-8') as f:
        f.write(reporte)

    # CSV de resultados
    todos = resultados_cedears + resultados_adrs + resultados_byma
    if todos:
        cols = ['ticker','score','zona','precio','ratio','precio_ars','stop_ars','target_ars','rsi','estructura']
        df = pd.DataFrame(todos)
        df[[c for c in cols if c in df.columns]].to_csv(os.path.join(settings.RESULTS_DIR, f'confluence_{date_str}.csv'), index=False)

    logger.info(f"Reporte generado: {fname_latest}")
    return reporte

def get_rotation(fetcher, scanner):
    """Calcula rotación sectorial."""
    spy_df = fetcher.ref_data.get('SPY')
    if spy_df is None:
        return [], 0
    # Asegurar que trabajamos con arrays 1D
    spy_c = spy_df['Close'].values.flatten()  # .flatten() garantiza 1D
    if len(spy_c) < settings.RS_DIAS + 1:
        return [], 0
    spy_ret = (spy_c[-1] / spy_c[-settings.RS_DIAS]) - 1
    rows = []
    for sector, etf in scanner.sector_etf.items():
        if etf in fetcher.ref_data:
            etf_df = fetcher.ref_data[etf]
            etf_c = etf_df['Close'].values.flatten()
            if len(etf_c) < settings.RS_DIAS + 1:
                continue
            etf_ret = (etf_c[-1] / etf_c[-settings.RS_DIAS]) - 1
            rs = (1 + etf_ret) / (1 + spy_ret) if (1 + spy_ret) != 0 else 0
            rows.append({
                'sector': sector,
                'etf': etf,
                'ret_5d': round(etf_ret * 100, 2),
                'rs_spy': round(rs, 3),
                'estado': 'ENTRANDO' if rs >= 1.0 else 'saliendo',
            })
    rows.sort(key=lambda x: x['rs_spy'], reverse=True)
    return rows, round(spy_ret * 100, 2)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['scan', 'bot', 'scheduler'], default='scan')
    args = parser.parse_args()

    if args.mode == 'scan':
        run_scan_and_generate_report()
    elif args.mode == 'bot':
        from bot.telegram_bot import SMCBot
        bot = SMCBot()
        bot.run()
    elif args.mode == 'scheduler':
        from scheduler.daily_job import run_scheduler
        run_scheduler()
