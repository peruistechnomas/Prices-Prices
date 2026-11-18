import json
import os
import re
import requests
from bs4 import BeautifulSoup

# Tus 8 enlaces exactos de Falabella
URLS = [
    "https://www.falabella.com.pe/falabella-pe/product/21414094/chompa-hombre-la-martina/21414096",
    "https://www.falabella.com.pe/falabella-pe/product/80172075/knit-polo/80172304",
    "https://www.falabella.com.pe/falabella-pe/product/80172058/short-sleeve-knit/80172242",
    "https://www.falabella.com.pe/falabella-pe/product/21062272/camisa-negro-s/80145407",
    "https://www.falabella.com.pe/falabella-pe/product/80183114/long-sleeve-sweatshirt/80183183",
    "https://www.falabella.com.pe/falabella-pe/product/20814027/polo-mc-cuello-office-blue-c1750-s/20814031",
    "https://www.falabella.com.pe/falabella-pe/product/80172053/classic-sport-cap/80172221",
    "https://www.falabella.com.pe/falabella-pe/product/21495609/sskccmslm1-shor/21495613",
]

DATA_FILE = "last_prices.json"

# Credenciales de tu Bot de Telegram
TELEGRAM_TOKEN = "8877774720:AAGZDgSvjTDU1veqxA1wsrHxDSM3J5QC37M"
CHAT_ID = "1301227407"


def send_telegram_message(message):
  """Envía una alerta directa a tu Telegram"""
  url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
  payload = {
      "chat_id": CHAT_ID,
      "text": message,
      "parse_mode": "Markdown",
  }
  try:
    requests.post(url, json=payload, timeout=10)
  except Exception as e:
    print(f"Error al enviar mensaje de Telegram: {e}")


def extract_sku(url):
  match = re.search(r"/product/(\d+)", url)
  if match:
    return match.group(1)
  parts = url.strip("/").split("/")
  for part in parts:
    if part.isdigit() and len(part) > 5:
      return part
  return None


def clean_price(price_str):
  """Convierte un string de precio a float para poder compararlos"""
  if not price_str or "no disponible" in price_str.lower():
    return None
  try:
    clean = (
        price_str.replace("S/", "")
        .replace("S/.", "")
        .replace(",", "")
        .strip()
    )
    return float(clean)
  except ValueError:
    return None


def get_product_info(url):
  sku = extract_sku(url)
  if not sku:
    return "Producto sin nombre", "Precio no disponible"

  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/122.0.0.0 Safari/537.36"
      ),
      "Accept": "application/json, text/plain, */*",
      "Accept-Language": "es-PE,es;q=0.9",
      "Referer": url,
      "Origin": "https://www.falabella.com.pe",
  }

  # Intento 1: API interna de Falabella
  api_url = f"https://www.falabella.com.pe/s/product/v1/pe/product/{sku}"
  try:
    response = requests.get(api_url, headers=headers, timeout=10)
    if response.status_code == 200:
      data = response.json()
      name = data.get("name") or data.get("productName")

      price = None
      prices_list = data.get("prices", [])
      for p in prices_list:
        if "formattedValue" in p:
          price = p["formattedValue"]
          break
        elif "price" in p:
          price = str(p["price"])
          break

      if name and price:
        return name, price
  except Exception:
    pass

  # Intento 2: Respaldo HTML directo
  try:
    response = requests.get(url, headers=headers, timeout=15)
    if response.status_code == 200:
      soup = BeautifulSoup(response.text, "html.parser")

      name_tag = soup.find(
          "h1", {"class": lambda x: x and "product" in x.lower()}
      ) or soup.find("h1")
      name = (
          name_tag.get_text(strip=True) if name_tag else "Producto sin nombre"
      )

      price_tag = soup.find(
          "span",
          {
              "class": lambda x: x
              and ("price" in x.lower() or "copy" in x.lower())
          },
      )
      price = (
          price_tag.get_text(strip=True)
          if price_tag
          else "Precio no disponible"
      )

      return name, price
  except Exception:
    pass

  return "Producto sin nombre", "Precio no disponible"


def main():
  old_prices = {}
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        old_prices = json.load(f)
    except Exception:
      pass

  current_prices = {}

  print("=== INICIANDO VERIFICACIÓN DE PRECIOS ===")

  for url in URLS:
    print(f"Consultando: {url}")
    name, price = get_product_info(url)
    current_prices[url] = {"name": name, "price": price}

    if url in old_prices:
      old_price_str = old_prices[url].get("price")
      old_val = clean_price(old_price_str)
      new_val = clean_price(price)

      if old_val and new_val:
        if new_val < old_val:
          # ¡Alerta de rebaja! Preparamos y enviamos el mensaje a Telegram
          msg = (
              f"📉 *¡BAJÓ DE PRECIO EN FALABELLA!*\n\n"
              f"👕 *Producto:* {name}\n"
              f"💰 *Precio anterior:* {old_price_str}\n"
              f"🔥 *Precio nuevo:* {price}\n\n"
              f"[Ver producto en Falabella]({url})"
          )
          print(f"¡Rebaja detectada en {name}! Enviando alerta a Telegram...")
          send_telegram_message(msg)
        elif new_val > old_val:
          print(f"   [Subió] {name} pasó de {old_price_str} a {price}")
        else:
          print(f"   [Sin cambios] {price}")
      else:
        print(f"   [Actual] {price}")
    else:
      print(f"   [Nuevo registro] {price}")

  # Guardar los precios actualizados
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(current_prices, f, ensure_ascii=False, indent=4)

  print("\n✅ Verificación completada.")


if __name__ == "__main__":
  main()
