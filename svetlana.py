import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = "8877774720:AAEvlIkejUrYW1wZNcwf95o0dm_LxWhW0Iw"
CHAT_ID = "1301227407"

def enviar_alerta(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    print(f"Respuesta de Telegram: {response.status_code}")
    return response.json()

if __name__ == "__main__":
    enviar_alerta("🤖 ¡Hola! Mensaje de prueba de Svetlana: el bot está activo y conectado con éxito.")
    print("Ejecución completada.")
