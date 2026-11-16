import json
import os
import re
import requests

# Tus URLs de productos de Falabella
URLS = [
    "https://www.falabella.com.pe/falabella-pe/product/2141...",
    "https://www.falabella.com.pe/falabella-pe/product/8018...",
    "https://www.falabella.com.pe/falabella-pe/product/8017...",
    "https://www.falabella.com.pe/falabella-pe/product/2106...",
]

DATA_FILE = "last_prices.json"


def extract_sku(url):
  # Extrae el número de SKU o ID del producto que está al final de la URL de Falabella
  match = re.search(r"/product/(\d+)", url)
  if match:
    return match.group(1)
  # Si el formato usa guiones al final (ej: /12345678)
  parts = url.strip("/").split("/")
  for part in parts:
    if part.isdigit() and len(part) > 5:
      return part
  return None


def get_product_info(url):
  sku = extract_sku(url)
  if not sku:
    return "Producto sin nombre", "Precio no disponible"

  # Cabeceras simulando un navegador real muy específico
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

  # Intento 1: Consultar mediante la API pública de productos de Falabella usando el SKU
  api_url = (
      f"https://www.falabella.com.pe/s/product/v1/pe/product/{sku}"
  )
  try:
    response = requests.get(api_url, headers=headers, timeout=10)
    if response.status_code == 200:
      data = response.json()
      # Extraer nombre y precio desde la respuesta de la API
      name = data.get("name") or data.get("productName")
      
      # Buscar el precio dentro de las estructuras habituales de la API
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

  # Intento 2 (Respaldo): Petición directa a la página web con cabeceras de navegador
  try:
    response = requests.get(url, headers=headers, timeout=15)
    if response.status_code == 200:
      from bs4import BeautifulSoup

      soup = BeautifulSoup(response.text, "html.parser")
      
      # Buscar título
      name_tag = soup.find("h1", {"class": lambda x: x and "product" in x.lower()}) or soup.find("h1")
      name = name_tag.get_text(strip=True) if name_tag else "Producto sin nombre"

      # Buscar precio en clases comunes de Falabella
      price_tag = soup.find("span", {"class": lambda x: x and ("price" in x.lower() or "copy" in x.lower())})
      price = price_tag.get_text(strip=True) if price_tag else "Precio no disponible"

      return name, price
  except Exception:
    pass

  return "Producto sin nombre", "Precio no disponible"


def main():
  current_prices = {}

  for url in URLS:
    print(f"Consultando SKU para: {url}")
    name, price = get_product_info(url)
    current_prices[url] = {"name": name, "price": price}

  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(current_prices, f, ensure_ascii=False, indent=4)

  print("Archivo last_prices.json actualizado con éxito mediante API.")


if __name__ == "__main__":
  main()
