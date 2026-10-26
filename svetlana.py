import requests
from bs4 import BeautifulSoup
import re
import json
import os
from playwright.sync_api import sync_playwright

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

def get_ripley_price_with_browser(url):
    """Usa un navegador real (Playwright) para extraer el precio de Ripley sin bloqueos."""
    found_price = None
    try:
        with sync_playwright() as p:
            # Lanzar un navegador Chromium en segundo plano (headless)
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page.goto(url, timeout=30000)
            
            # Esperar a que cargue algún elemento de precio en la página
            try:
                page.wait_for_selector('.product-price, .internet-price, [class*="price"]', timeout=10000)
            except Exception:
                pass # Si no espera el selector exacto, igual leemos el HTML renderizado
            
            html_content = page.content()
            browser.close()
            
            # Buscar el precio en el HTML ya renderizado por el navegador
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Buscar en etiquetas comunes de precios de Ripley
            price_tags = soup.find_all(['li', 'div', 'span', 'p'], class_=re.compile(r'price|internet|normal|card', re.I))
            for tag in price_tags:
                match = re.search(r'S/\s*([\d.,]+)', tag.text)
                if match:
                    val_str = match.group(1).replace(',', '')
                    try:
                        val = float(val_str)
                        if 10 <= val <= 2000:
                            found_price = val
                            break
                    except ValueError:
                        continue
            
            # Respaldo general si las clases cambiaron
            if not found_price:
                all_text = soup.find_all(string=re.compile(r'S/\s*\d+'))
                for elem in all_text:
                    match = re.search(r'S/\s*([\d.,]+)', elem)
                    if match:
                        val_str = match.group(1).replace(',', '')
                        try:
                            val = float(val_str)
                            if 10 <= val <= 2000:
                                found_price = val
                                break
                        except ValueError:
                            continue
                            
    except Exception as e:
        print(f"Error with Playwright for Ripley: {e}")
        
    return found_price

def check_prices():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "es-PE,es;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }
    
    products = [
        {
            "id": "la_martina_falabella",
            "name": "Sweater La Martina (Falabella)",
            "url": "https://www.falabella.com.pe/falabella-pe/product/21414094/chompa-hombre-la-martina/21414096",
            "price_limit": 200.00,
            "store": "falabella"
        },
        {
            "id": "pantalon_spavaldi",
            "name": "Pantalon Spavaldi Ezio (Ripley)",
            "url": "https://simple.ripley.com.pe/pantalon-hombre-spavaldi-ezio-2005364407890?color_80=Arena&s=mdco&pos=9&catPos=9&p=1&ps=39&orig=PSP&searchTerm=Spavaldi",
            "price_limit": 120.00,
            "store": "ripley"
        },
        {
            "id": "casaca_spavaldi",
            "name": "Casaca Spavaldi Beata (Ripley)",
            "url": "https://simple.ripley.com.pe/casaca-hombre-spavaldi-beata-2005370113310?color_80=Caf%C3%A9&s=mdco&pos=13&catPos=13&p=1&ps=39&orig=PSP&searchTerm=Spavaldi",
            "price_limit": 150.00,
            "store": "ripley"
        },
        {
            "id": "polo_lino_spavaldi",
            "name": "Polo Manga Corta Lino Spavaldi (Ripley)",
            "url": "https://simple.ripley.com.pe/polo-manga-corta-lino-spavaldi-azul-marino-2005370112030?color_80=Blanco&s=mdco&pos=32&catPos=32&p=1&ps=39&orig=PSP&searchTerm=Spavaldi",
            "price_limit": 80.00,
            "store": "ripley"
        },
        {
            "id": "polo_algodon_marquis",
            "name": "Polo Manga Corta Algodon Marquis (Ripley)",
            "url": "https://simple.ripley.com.pe/polo-manga-corta-algodon-hombre-marquis-2005373327929?color_80=Caf%C3%A9&s=mdco&pos=13&catPos=61&p=2&ps=48&cat=marquis_casual_homb&orig=PLP&prodNavFullCategory=Hombre+%3E+Marcas+casuales+%3E+Marquis",
            "price_limit": 70.00,
            "store": "ripley"
        }
    ]
    
    last_prices = load_last_prices()
    updated_prices = last_prices.copy()
    
    for prod in products:
        prod_id = prod["id"]
        found_price = None
        
        print(f"Checking: {prod['name']}...")
        
        if prod["store"] == "ripley":
            found_price = get_ripley_price_with_browser(prod["url"])
        else:
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
                print(f"Error checking Falabella {prod['name']}: {e}")
                
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
