import json
import os
import requests
from bs4 import BeautifulSoup

# Lista de tus productos a monitorear
URLS = [
    "https://www.falabella.com.pe/falabella-pe/product/2141...",  # Reemplaza con tus URLs reales si es necesario
    "https://www.falabella.com.pe/falabella-pe/product/8018...",
    "https://www.falabella.com.pe/falabella-pe/product/8017...",
    "https://www.falabella.com.pe/falabella-pe/product/8017...",
    "https://www.falabella.com.pe/falabella-pe/product/8017...",
    "https://www.falabella.com.pe/falabella-pe/product/8017...",
    "https://www.falabella.com.pe/falabella-pe/product/2106...",
    "https://www.falabella.com.pe/falabella-pe/product/8017...",
]

DATA_FILE = "last_prices.json"


def get_product_info(url):
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/122.0.0.0 Safari/537.36"
      ),
      "Accept-Language": "es-PE,es;q=0.9",
      "Accept": (
          "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
      ),
  }

  try:
    response = requests.get(url, headers=headers, timeout=15)
    if response.status_code != 200:
      return "Producto sin nombre", "Precio no disponible"

    soup = BeautifulSoup(response.text, "html.parser")
    name = "Producto sin nombre"
    price = "Precio no disponible"

    # Método 1: Buscar en el JSON interno __NEXT_DATA__ (la forma más precisa en Falabella)
    script_tag = soup.find("script", id="__NEXT_DATA__")
    if script_tag:
      try:
        json_data = json.loads(script_tag.string)
        # Navegamos por la estructura típica de Next.js de Falabella
        # (Esto puede variar según el diseño exacto de la API de la tienda)
        product_info = (
            json_data.get("props", {})
            .get("pageProps", {})
            .get("product", {})
        )
        if product_info:
          name = product_info.get("name", "Producto sin nombre")
          # Buscar precios en las variantes o bloques de precios
          prices = product_info.get("prices", [])
          if prices:
            # Intenta capturar el precio normal o de oferta
            price = str(prices[0].get("price", [p.get("formattedValue") for p in prices][0] if prices else "Precio no disponible"))
        # Si no lo halló directo, buscamos de forma genérica en el JSON
        if name == "Producto sin nombre":
          # Fallback de texto con BeautifulSoup si el JSON falla en esta capa
          pass
      except Exception:
        pass

    # Método 2: Respaldo buscando etiquetas HTML comunes si el JSON no dio el precio
    if price == "Precio no disponible":
      # Buscar título en etiquetas h1 o meta tags
      h1_tag = soup.find("h1")
      if h1_tag:
        name = h1_tag.get_text(strip=True)

      # Buscar clases comunes de precio en Falabella Perú
      price_tag = soup.find("span", {"class": lambda x: x and "prices" in x.lower()}) or \
                  soup.find("li", {"class": lambda x: x and "price" in x.lower()})
      if price_tag:
        price = price_tag.get_text(strip=True)

    return name, price

  except Exception as e:
    print(f"Error al conectar con {url}: {e}")
    return "Producto sin nombre", "Precio no disponible"


def main():
  current_prices = {}

  # Cargar precios anteriores si existen
  old_prices = {}
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        old_prices = json.load(f)
    except Exception:
      old_prices = {}

  # Analizar cada URL
  for url in URLS:
    print(f"Consultando: {url}")
    name, price = get_product_info(url)
    current_prices[url] = {"name": name, "price": price}

  # Guardar los nuevos precios en el archivo JSON
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(current_prices, f, ensure_ascii=False, indent=4)

  print("Archivo last_prices.json actualizado correctamente.")


if __name__ == "__main__":
  main()
