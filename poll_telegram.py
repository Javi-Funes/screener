import os
import requests
import subprocess
import json
from pathlib import Path

# Configuración
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

def get_last_update_id():
    if Path(LAST_UPDATE_FILE).exists():
        with open(LAST_UPDATE_FILE, "r") as f:
            return int(f.read().strip())
    return 0

def save_last_update_id(update_id):
    with open(LAST_UPDATE_FILE, "w") as f:
        f.write(str(update_id))

def main():
    offset = get_last_update_id() + 1
    updates = get_updates(offset)
    if not updates.get("ok"):
        print("Error obteniendo updates")
        return

    for update in updates["result"]:
        update_id = update["update_id"]
        message = update.get("message")
        if not message:
            continue

        chat_id = message["chat"]["id"]
        # Solo respondemos a nuestro chat autorizado
        if str(chat_id) != CHAT_ID:
            continue

        text = message.get("text", "")
        if text == "/report":
            # Ejecutar el escaneo
            send_message("🔄 Generando reporte, espera unos segundos...")
            # Llamar al script de escaneo
            result = subprocess.run(["python", "main.py", "--mode", "scan"], capture_output=True, text=True)
            if result.returncode != 0:
                send_message(f"Error en el escaneo:\n{result.stderr}")
            else:
                # Leer el reporte generado
                report_path = "results/reporte_latest.txt"
                if os.path.exists(report_path):
                    with open(report_path, "r", encoding="utf-8") as f:
                        reporte = f.read()
                    # Enviar en partes (máx 4096)
                    for i in range(0, len(reporte), 4000):
                        send_message(reporte[i:i+4000])
                else:
                    send_message("No se pudo generar el reporte.")
        elif text == "/start":
            send_message("Bot SMC activo. Usa /report para obtener el último reporte.")
        elif text == "/help":
            send_message("Comandos:\n/report - Obtener reporte actualizado\n/start - Iniciar\n/help - Ayuda")
        else:
            send_message("Comando no reconocido. Usa /help")

        # Actualizar último update_id procesado
        offset = update_id + 1

    save_last_update_id(offset - 1)

if __name__ == "__main__":
    main()
