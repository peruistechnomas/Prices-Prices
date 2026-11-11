import os
import json
import requests
from bs4얀 import BeautifulSoup

# Lista definitiva de los 8 productos en Falabella
URLS = [
    "https://www.falabella.com.pe/falabella-pe/product/21414094/chompa-hombre-la-martina/21414099",
    "https://www.falabella.com.pe/falabella-pe/product/80183114/long-sleeve-sweatshirt/80183183",
    "https://www.falabella.com.pe/falabella-pe/product/80172057/short-sleeve-sport-shirt/80172235",
    "https://www.falabella.com.pe/falabella-pe/product/80172081/short-sleeve-knit/80172332",
    "https://www.falabella.com.pe/falabella-pe/product/80172058/short-sleeve-knit/80172241",
    "https://www.falabella.com.pe/falabella-pe/product/80172092/short-sleeve-knit/80172370",
    "https://www.falabella.com.pe/falabella-pe/product/21062272/camisa-negro-s/80145409",
    "https://www.falabella.com.pe/falabella-pe/product/80172053/classic-sport-cap/80172221"
]

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
STATE_FILE = "last_prices.json"

def send_telegram_message(text):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Telegram tokens no configurados.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Error al enviar mensaje a Telegram: {e}")

def load_previous_prices():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_current_prices(prices):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(prices, f, ensure_ascii=False, indent=4)

def check_prices():
    previous_prices = load_previous_prices()
    current_prices = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    for url in URLS:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                print(f"Error HTTP {response.status_code} en {url}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            next_data = soup.find("script", id="__NEXT_DATA__")
            
            if not next_data:
                print(f"No se encontró __NEXT_DATA__ en {url}")
                continue

            data = json.loads(next_data.string)
            
            # Extracción segura a través del árbol JSON de Falabella
            product_data = data.get("props", {}).get("pageProps", {}).get("product", {})
            name = product_data.get("name", "Producto sin nombre")
            
            # Buscar precios en las variantes o bloques de precios
            prices_list = product_data.get("prices", [])
            current_price = None
            for p in prices_list:
                # Buscamos el precio internet u oferta principal
                if p.get("type") in ["NORMAL", "INTERNET", "OFFER"]:
                    current_price = p.get("price", [None])[0]
                    if current_price:
                        break
            
            if not current_price:
                # Fallback genérico si la estructura varía
                current_price = product_data.get("currentPrice") or "Precio no disponible"

            current_prices[url] = {
                "name": name,
                "price": current_price
            }

            # Lógica de comparación y alerta si baja el precio
            old_entry = previous_prices.get(url)
            if old_entry and old_entry.get("price") != current_price:
                old_val = old_entry.get("price")
                msg = f"🚨 *¡ALERTA DE PRECIO!*\n\n*{name}*\nPrecio anterior: {old_val}\nPrecio actual: {current_price}\n\n[Ver producto]({url})"
                send_telegram_message(msg)

        except Exception as e:
            print(f"Error procesando {url}: {e}")

    save_current_prices(current_prices)

if __name__ == "__main__":
    check_prices()
