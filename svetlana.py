import json
import os
import re
import requests
from bs4 import BeautifulSoup

# Tus 8 enlaces exactos y completos de Falabella
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


def extract_sku(url):
  match = re.search(r"/product/(\d+)", url)
  if match:
    return match.group(1)
  parts = url.strip("/").split("/")
  for part in parts:
    if part.isdigit() and len(part) > 5:
      return part
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
  current_prices = {}

  for url in URLS:
    print(f"Consultando producto: {url}")
    name, price = get_product_info(url)
    current_prices[url] = {"name": name, "price": price}

  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(current_prices, f, ensure_ascii=False, indent=4)

  print("Archivo last_prices.json actualizado correctamente.")


if __name__ == "__main__":
  main()
