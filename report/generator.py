from datetime import datetime
from typing import List, Dict, Tuple
from config import settings

def generar_reporte(ccl: float, ccl_fuente: str,
                    resultados_cedears: List[Dict],
                    resultados_adrs: List[Dict],
                    resultados_byma: List[Dict],
                    rotacion: List[Dict],
                    spy_ret: float) -> str:
    """Genera reporte en formato texto."""
    now = datetime.now().strftime('%d/%m/%Y %H:%M')
    lines = []
    def L(txt=''): lines.append(txt)

    L('=' * 65)
    L('   SMC CONFLUENCE SCREENER — REPORTE DIARIO')
    L(f'   {now} (ARG) — Swing Length: {settings.SWING_LENGTH} (LuxAlgo)')
    L('=' * 65)
    L()
    L(f'  CCL: ${ccl:,.2f} pesos/USD  (fuente: {ccl_fuente})')
    L()
    # ... (similar al original, pero usando settings en lugar de constantes)
    # Por brevedad, omito el resto del reporte que es idéntico, solo adaptando imports.
    # Se puede copiar la función original y reemplazar las variables globales por settings.

    return '\n'.join(lines)
