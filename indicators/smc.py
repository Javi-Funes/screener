import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Optional
from config import settings

def to_arr(s):
    return np.array(s).flatten()

def calculate_rsi(prices, period=14):
    """Calcula RSI usando EMA."""
    delta = prices.diff()
    gain = delta.clip(lower=0).ewm(com=period-1, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(com=period-1, min_periods=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return to_arr(rsi)

def find_swings(high, low, length):
    """Encuentra swings máximos y mínimos locales con ventana 'length'."""
    sh, sl = [], []
    for i in range(length, len(high)):
        if high[i-length] == max(high[i-length:i]):
            sh.append((i-length, float(high[i-length])))
        if low[i-length] == min(low[i-length:i]):
            sl.append((i-length, float(low[i-length])))
    return sh, sl

def get_zones(top, bottom):
    """Calcula zonas de interés a partir del rango."""
    r = top - bottom
    return {
        'discount': (bottom, bottom + settings.DISCOUNT_PCT * r),
        'near_discount': (bottom, bottom + settings.NEAR_DISCOUNT_PCT * r),
        'equilibrium': (bottom + (0.5 - settings.EQUILIBRIUM_BAND) * r,
                        bottom + (0.5 + settings.EQUILIBRIUM_BAND) * r),
        'premium': (top - settings.DISCOUNT_PCT * r, top),
    }

def get_estructura(sh, sl):
    """Determina estructura de mercado basada en últimos swings."""
    if len(sh) < 2 or len(sl) < 2:
        return 'Indefinida'
    uh = [v for _, v in sh[-3:]]
    ul = [v for _, v in sl[-3:]]
    hh = all(uh[i] > uh[i-1] for i in range(1, len(uh)))
    hl = all(ul[i] > ul[i-1] for i in range(1, len(ul)))
    lh = all(uh[i] < uh[i-1] for i in range(1, len(uh)))
    ll = all(ul[i] < ul[i-1] for i in range(1, len(ul)))
    if hh and hl: return 'Alcista'
    if lh and ll: return 'Bajista'
    if hh or hl:  return 'Alcista Debil'
    if lh or ll:  return 'Bajista Debil'
    return 'Lateral'

def detect_ob_encima(high, low, close, price, sh):
    """Detecta Order Block por encima del precio actual (mejorado)."""
    if not sh:
        return False, None
    # Tomamos el último swing high
    last_idx, last_val = sh[-1]
    # Buscamos una vela con cuerpo pequeño y mecha larga por debajo, después del swing
    for i in range(last_idx + 1, min(len(close), last_idx + 10)):
        # Condición: vela bajista o alcista? Para OB alcista, buscamos una vela bajista que luego sea soporte
        # Simplificamos: buscamos una vela donde el cierre esté por encima del mínimo y el mínimo sea un soporte posterior
        # En lugar de eso, usamos la lógica original mejorada con rango más claro:
        # OB es la última vela antes de un movimiento impulsivo, pero aquí lo dejamos simple.
        # Reimplementación más estándar:
        # OB = vela con cuerpo pequeño, mecha inferior larga, y que posteriormente el precio la respeta.
        pass
    # Por ahora mantenemos la lógica original, pero corregimos el rango
    if not sh:
        return False, None
    idx = sh[-1][0]
    # Buscar hacia atrás desde idx+3 hasta idx-8, pero asegurando índices válidos
    start = min(len(close)-1, idx+3)
    end = max(1, idx-8)
    if start <= end:
        return False, None
    for i in range(start, end, -1):
        if close[i] > close[i-1]:
            ob_l = float(low[i])
            if ob_l > price and ob_l < price * 1.08:
                return True, round(ob_l, 2)
    return False, None

def detect_fvg_all(high, low, close, price, lookback=30):
    """Detecta Fair Value Gaps en los últimos 'lookback' períodos."""
    fvgs = []
    n = min(lookback, len(close) - 2)
    for i in range(2, n + 2):
        idx = -i
        try:
            h0 = float(high[idx-1])
            l0 = float(low[idx-1])
            h2 = float(high[idx+1])
            l2 = float(low[idx+1])
        except IndexError:
            continue
        # FVG alcista (gap hacia arriba)
        if l2 > h0:
            gap_low = round(h0, 2)
            gap_high = round(l2, 2)
            if price > gap_low:
                dist_pct = round((gap_low - price) / price * 100, 2)
                fvgs.append({
                    'tipo': 'BULLISH',
                    'low': gap_low,
                    'high': gap_high,
                    'mid': round((gap_low + gap_high) / 2, 2),
                    'dist_pct': dist_pct,
                    'relacion': 'DEBAJO' if gap_low < price else 'ENCIMA',
                })
        # FVG bajista (gap hacia abajo)
        if h2 < l0:
            gap_low = round(h2, 2)
            gap_high = round(l0, 2)
            if price < gap_high:
                dist_pct = round((gap_high - price) / price * 100, 2)
                fvgs.append({
                    'tipo': 'BEARISH',
                    'low': gap_low,
                    'high': gap_high,
                    'mid': round((gap_low + gap_high) / 2, 2),
                    'dist_pct': dist_pct,
                    'relacion': 'ENCIMA' if gap_high > price else 'DEBAJO',
                })
    # Eliminar duplicados cercanos
    unique = []
    for fvg in fvgs:
        es_dup = any(abs(f['mid'] - fvg['mid']) / fvg['mid'] < 0.005 for f in unique)
        if not es_dup:
            unique.append(fvg)
    unique.sort(key=lambda x: abs(x['dist_pct']))
    return unique[:6]

def calc_fibonacci_pois(sh, sl, price):
    """Calcula niveles de Fibonacci basados en el último swing relevante."""
    if not sh or not sl:
        return [], []
    # Buscar el último swing high
    last_sh_idx, last_sh_val = sh[-1]
    # Buscar el swing low más reciente anterior a ese high
    sl_antes = [(i, v) for i, v in sl if i < last_sh_idx]
    if not sl_antes:
        return [], []
    imp_low_idx, imp_low = sl_antes[-1]
    imp_high = last_sh_val
    rango_imp = imp_high - imp_low
    if rango_imp <= 0:
        return [], []
    niveles_fib = [0.236, 0.382, 0.5, 0.618, 0.65, 0.786]
    nombres_fib = {
        0.236: '23.6% — Retroceso menor',
        0.382: '38.2% — POI moderado',
        0.500: '50.0% — Equilibrium',
        0.618: '61.8% — Golden Pocket',
        0.650: '65.0% — Golden Pocket ext.',
        0.786: '78.6% — Ultimo soporte',
    }
    retrocesos = []
    for nivel in niveles_fib:
        precio_fib = round(imp_high - (rango_imp * nivel), 2)
        dist = round((precio_fib - price) / price * 100, 2)
        retrocesos.append({
            'nivel': nivel,
            'nombre': nombres_fib[nivel],
            'precio': precio_fib,
            'dist_pct': dist,
            'zona': 'SOPORTE' if precio_fib < price else 'RESISTENCIA',
            'es_golden': nivel in [0.618, 0.65],
        })
    extensiones = []
    for nivel, nombre in [(1.272, '127.2% — Extension 1'),
                          (1.414, '141.4% — Extension 2'),
                          (1.618, '161.8% — Extension dorada')]:
        precio_ext = round(imp_low + (rango_imp * nivel), 2)
        dist = round((precio_ext - price) / price * 100, 2)
        extensiones.append({
            'nivel': nivel,
            'nombre': nombre,
            'precio': precio_ext,
            'dist_pct': dist
        })
    return retrocesos, extensiones

def detect_absorcion(vol, close, high, low):
    """Detecta absorción: volumen alto + cierre en la parte alta."""
    if len(vol) < 25:
        return False, 0
    avg_vol = float(np.mean(vol[-21:-1]))
    if avg_vol == 0:
        return False, 0
    for lb in range(1, 4):
        vr = float(vol[-lb]) / avg_vol
        rango = float(high[-lb]) - float(low[-lb])
        if rango == 0:
            continue
        cp = (float(close[-lb]) - float(low[-lb])) / rango
        if vr >= settings.ABSORCION_VOL_RATIO and cp >= 0.70:
            return True, round(vr, 2)
    return False, 0

def detect_squeeze(high, low):
    """Detecta squeeze: reducción de rango."""
    if len(high) < 20:
        return False
    rangos = high - low
    r_act = float(np.mean(rangos[-3:]))
    r_prev = float(np.mean(rangos[-20:-3]))
    if r_prev == 0:
        return False
    return (r_act / r_prev) <= settings.SQUEEZE_RATIO
