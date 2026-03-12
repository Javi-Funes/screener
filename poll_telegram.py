import os
import requests
import subprocess
import json
from pathlib import Path

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
LAST_UPDATE_FILE = "last_update_id.txt"

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    resp = requests.get(url, params=params)
    return resp.json()

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, json=payload)

def send_long_message(text):
    """Divide mensajes largos en partes de 4000 caracteres"""
    for i in range(0, len(text), 4000):
        send_message(text[i:i+4000])

def get_last_update_id():
    if Path(LAST_UPDATE_FILE).exists():
        with open(LAST_UPDATE_FILE, "r") as f:
            return int(f.read().strip())
    return 0

def save_last_update_id(update_id):
    with open(LAST_UPDATE_FILE, "w") as f:
        f.write(str(update_id))

def run_scan():
    """Ejecuta el escaneo y devuelve el reporte como string"""
    # Enviar un mensaje de "espera" para que el usuario sepa que está procesando
    send_message("🔄 Generando nuevo reporte, por favor espera... (esto puede tomar hasta 30 segundos)")
    
    # Ejecutar el comando de escaneo
    result = subprocess.run(
        ["python", "main.py", "--mode", "scan"],
        capture_output=True,
        text=True,
        timeout=120  # tiempo máximo de espera (2 minutos)
    )
    
    if result.returncode != 0:
        error_msg = f"Error en el escaneo:\n{result.stderr}"
        send_message(error_msg)
        return None
    
    # Leer el reporte generado
    report_path = "results/reporte_latest.txt"
    if Path(report_path).exists():
        with open(report_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        send_message("No se pudo encontrar el reporte generado.")
        return None

def main():
    offset = get_last_update_id() + 1
    updates = get_updates(offset)
    
    if not updates.get("ok"):
        print("Error obteniendo updates")
        return
    
    for update in updates.get("result", []):
        update_id = update["update_id"]
        message = update.get("message")
        if not message:
            continue
        
        # Verificar que el mensaje sea de nuestro chat autorizado
        chat_id = str(message["chat"]["id"])
        if chat_id != CHAT_ID:
            continue
        
        text = message.get("text", "")
        
        if text == "/start":
            send_message("Bot SMC activo. Usá /report para obtener un reporte nuevo.")
        
        elif text == "/help":
            send_message("Comandos:\n/report - Generar y recibir un reporte nuevo\n/start - Iniciar\n/help - Ayuda")
        
        elif text == "/report":
            reporte = run_scan()
            if reporte:
                send_long_message(reporte)
        
        else:
            send_message("Comando no reconocido. Usá /help")
        
        # Actualizar el último update_id procesado
        offset = update_id + 1
    
    save_last_update_id(offset - 1)

if __name__ == "__main__":
    main()
