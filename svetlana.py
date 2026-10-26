import json
import os
import re
import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = "8877774720:AAGZDgSvjTDU1veqxA1wsrHxDSM3J5QC37M"
CHAT_ID = "1301227407"
STATE_FILE = "last_prices.json"


def send_alert(message):
  """Envia una notificación formateada a tu chat de Telegram."""
  url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
  payload = {
      "chat_id": CHAT_ID,
      "text": message,
      "parse_mode": "Markdown",
      "disable_web_page_preview": True,
  }
  try:
    response = requests.post(url, json=payload, timeout=10)
    print(f"Telegram response status: {response.status_code}")
    return response.json()
  except Exception as e:
    print(f"Error sending Telegram message: {e}")
    return None


def load_last_prices():
  """Carga los precios registrados previamente."""
  if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r", encoding="utf-8") as f:
      try:
        return json.load(f)
      except Exception:
        return {}
  return {}


def save_last_prices(prices):
  """Guarda los precios actuales en el archivo local."""
  with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump(prices, f, indent=4, ensure_ascii=False)


def check_prices():
  # Headers simulando un navegador real para evitar bloqueos
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/124.0.0.0 Safari/537.36"
      ),
      "Accept-Language": "es-PE,es;q=0.9,en;q=0.8",
      "Accept": (
          "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
      ),
      "Connection": "keep-alive",
  }

  products = [{
      "id": "la_martina_falabella",
      "name": "Sweater La Martina (Falabella)",
      "url": (
          "https://www.falabella.com.pe/falabella-pe/product/21414094/chompa-hombre-la-martina/21414096"
      ),
      "price_limit": 200.00,
  }]

  last_prices = load_last_prices()
  updated_prices = last_prices.copy()

  for prod in products:
    prod_id = prod["id"]
    found_price = None

    print(f"Checking: {prod['name']}...")

    try:
      response = requests.get(prod["url"], headers=headers, timeout=20)
      print(f"HTTP Status Code: {response.status_code}")

      if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        # Búsqueda ampliada de etiquetas de precio
        price_tags = soup.find_all(
            ["li", "div", "span", "p", "section"],
            class_=re.compile(r"price|internet|normal|copy10", re.I),
        )

        for tag in price_tags:
          match = re.search(r"S/\s*([\d.,]+)", tag.text)
          if match:
            val_str = match.group(1).replace(",", "")
            try:
              val = float(val_str)
              if 20 <= val <= 5000:
                found_price = val
                break
            except ValueError:
              continue

        # Plan de respaldo si no encuentra por clases
        if not found_price:
          price_elements = soup.find_all(string=re.compile(r"S/\s*\d+"))
          for elem in price_elements:
            match = re.search(r"S/\s*([\d.,]+)", elem)
            if match:
              val_str = match.group(1).replace(",", "")
              try:
                val = float(val_str)
                if 20 <= val <= 5000:
                  found_price = val
                  break
              except ValueError:
                continue
      else:
        # Si Falabella bloquea o da error (ej. 403 Forbidden)
        send_alert(
            f"⚠️ *Alerta del Bot*\nFalabella devolvió el código de estado"
            f" `{response.status_code}` al intentar revisar *{prod['name']}*."
        )

    except Exception as e:
      print(f"Error checking {prod['name']}: {e}")
      send_alert(
          f"❌ *Error técnico en el Bot*\nNo se pudo conectar con"
          f" *{prod['name']}*: `{e}`"
      )

    if found_price:
      old_price = last_prices.get(prod_id)
      updated_prices[prod_id] = found_price

      product_link = f"[Ver producto]({prod['url']})"

      if old_price is None:
        send_alert(
            f"Kevin, este es el precio inicial:\n\n📦 *{prod['name']}*\n💰 S/"
            f" {found_price:.2f}\n🔗 {product_link}"
        )
      elif found_price != old_price:
        trend = "📉 ¡Bajó!" if found_price < old_price else "📈 ¡Subió!"
        message = (
            f"Kevin, cambiaron los precios:\n\n📦 *{prod['name']}*\n🔄 Antes: S/"
            f" {old_price:.2f}\n💰 Ahora: S/ {found_price:.2f}"
            f" {trend}\n🔗 {product_link}"
        )
        if found_price <= prod["price_limit"]:
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
