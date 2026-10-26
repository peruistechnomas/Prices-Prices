import requests
from bs4 import BeautifulSoup
import re
import json
import os

TELEGRAM_TOKEN = "8877774720:AAGZDgSvjTDU1veqxA1wsrHxDSM3J5QC37M"
CHAT_ID = "1301227407"
STATE_FILE = "last_prices.json"

def send_alert(message):
    """Sends a formatted notification to your Telegram chat."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    response = requests.post(url, json=payload)
    print(f"Telegram response status: {response.status_code}")
    return response.json()

def load_last_prices():
    """Loads previously recorded prices from a local file."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}

def save_last_prices(prices):
    """Saves current prices to the local file for future runs."""
    with open(STATE_FILE, "w") as f:
        json.dump(prices, f, indent=4)

def check_prices():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "es-PE,es;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }
    
    # Lista de productos de Falabella (puedes agregar más aquí cuando quieras)
    products = [
        {
            "id": "la_martina_falabella",
            "name": "Sweater La Martina (Falabella)",
            "url": "https://www.falabella.com.pe/falabella-pe/product/21414094/chompa-hombre-la-martina/21414096",
            "price_limit": 200.00
        }
    ]
    
    last_prices = load_last_prices()
    updated_prices = last_prices.copy()
    
    for prod in products:
        prod_id = prod["id"]
        found_price = None
        
        print(f"Checking: {prod['name']}...")
        
        try:
            response = requests.get(prod['url'], headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                price_tags = soup.find_all(['li', 'div', 'span', 'p'], class_=re.compile(r'price|internet|normal', re.I))
                
                for tag in price_tags:
                    match = re.search(r'S/\s*([\d.,]+)', tag.text)
                    if match:
                        val_str = match.group(1).replace(',', '')
                        try:
                            val = float(val_str)
                            if 20 <= val <= 2000:
                                found_price = val
                                break
                        except ValueError:
                            continue
                
                if not found_price:
                    price_elements = soup.find_all(string=re.compile(r'S/\s*\d+'))
                    for elem in price_elements:
                        match = re.search(r'S/\s*([\d.,]+)', elem)
                        if match:
                            val_str = match.group(1).replace(',', '')
                            try:
                                val = float(val_str)
                                if 20 <= val <= 2000:
                                    found_price = val
                                    break
                            except ValueError:
                                continue
        except Exception as e:
            print(f"Error checking {prod['name']}: {e}")
                
        if found_price:
            old_price = last_prices.get(prod_id)
            updated_prices[prod_id] = found_price
            
            product_link = f"[Ver producto]({prod['url']})"
            
            if old_price is None:
                send_alert(
                    f"Kevin, estos son los precios:\n\n"
                    f"📦 *{prod['name']}*\n"
                    f"💰 S/ {found_price:.2f}\n"
                    f"🔗 {product_link}"
                )
            elif found_price != old_price:
                trend = "📉 ¡Bajó!" if found_price < old_price else "📈 ¡Subió!"
                message = (
                    f"Kevin, cambiaron los precios:\n\n"
                    f"📦 *{prod['name']}*\n"
                    f"🔄 Antes: S/ {old_price:.2f}\n"
                    f"💰 Ahora: S/ {found_price:.2f} {trend}\n"
                    f"🔗 {product_link}"
                )
                if found_price <= prod['price_limit']:
                    message += f"\n\n🎯 *¡Llegó a tu precio objetivo!*"
                send_alert(message)
            else:
                print(f"No price change for {prod['name']} (S/ {found_price:.2f})")
        else:
            print(f"Could not extract price for {prod['name']}")
            
    save_last_prices(updated_prices)

if __name__ == "__main__":
    check_prices()
    print("Execution completed.")
