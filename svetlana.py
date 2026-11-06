import json
import os
import re
import requests
from bs4 import BeautifulSoup

PRODUCTS_TO_TRACK = [
    {
        "id": "chompa_estrella_la_martina",
        "name": "Chompa Hombre La Martina (Específica)",
        "url": "https://www.falabella.com.pe/falabella-pe/product/21414094/chompa-hombre-la-martina/21414099",
    },
    {
        "id": "long_sleeve_sweatshirt_80183183",
        "name": "Long Sleeve Sweatshirt",
        "url": "https://www.falabella.com.pe/falabella-pe/product/80183114/long-sleeve-sweatshirt/80183183",
    },
    {
        "id": "sweater_top_m_s_ryl_ht_80096202",
        "name": "Sweater Top M S Ryl Ht",
        "url": "https://www.falabella.com.pe/falabella-pe/product/80096058/sweater-top-m-s-ryl-ht/80096202",
    },
    {
        "id": "short_sleeve_knit_80172241",
        "name": "Short Sleeve Knit",
        "url": "https://www.falabella.com.pe/falabella-pe/product/80172058/short-sleeve-knit/80172241",
    },
    {
        "id": "polo_ralph_lauren_21475966",
        "name": "Polo Polo Ralph Lauren",
        "url": "https://www.falabella.com.pe/falabella-pe/product/21436383/polo-polo-ralph-lauren/21475966",
    },
    {
        "id": "classic_sport_cap_80172221",
        "name": "Classic Sport Cap",
        "url": "https://www.falabella.com.pe/falabella-pe/product/80172053/classic-sport-cap/80172221",
    },
    {
        "id": "polo_pc_1950_nac_21461140",
        "name": "Polo PC 1950 Nac",
        "url": "https://www.falabella.com.pe/falabella-pe/product/21461129/polo-pc-1950-nac/21461140",
    },
    {
        "id": "polo_mc_cuello_pc_kils_lm_883862299",
        "name": "Polo M C Cuello PC Kils Lm",
        "url": "https://www.falabella.com.pe/falabella-pe/product/883862295/polo-m-c-cuello-pc-kils-lm/883862299",
    },
]

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9",
}

DATA_FILE = "last_prices.json"


def load_previous_data():
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        print(f"Memoria cargada. Productos en archivo: {len(data)}")
        return data
    except Exception as e:
      print(f"Error leyendo memoria JSON: {e}")
      return {}
  print("No hay memoria previa. Se creará una base nueva.")
  return {}


def save_current_data(data):
  try:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Memoria guardada con {len(data)} elementos.")
  except Exception as e:
    print(f"Error al guardar memoria: {e}")


def send_telegram_message(message):
  if not TELEGRAM_TOKEN or not CHAT_ID:
    print("Credenciales de Telegram no configuradas.")
    return
  url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
  payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
  try:
    res = requests.post(url, json=payload, timeout=30)
    if res.status_code == 200:
      print("¡Alerta enviada a Telegram con éxito!")
    else:
      print(f"Error de Telegram: {res.text}")
  except Exception as e:
    print(f"Error al enviar mensaje a Telegram: {e}")


def extract_price_from_next_data(html):
  """Busca el estado interno __NEXT_DATA__ o extrae los números de precio en el HTML."""
  try:
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    if match:
      data = json.loads(match.group(1))
      # Buscar dentro del árbol JSON de Falabella los precios del producto
      page_props = data.get("props", {}).get("pageProps", {})
      product_data = page_props.get("productData", {}) or page_props.get(
          "initialData", {}
      )

      # Intentar extraer de prices dentro de productData
      prices = product_data.get("prices", [])
      if not prices:
        # Fallback a variantes/skus si existen
        skus = product_data.get("variants", []) or product_data.get("skus", [])
        if skus and isinstance(skus, list) and len(skus) > 0:
          prices = skus[0].get("prices", [])

      for p in prices:
        price_val = p.get("price", [None])[0] if isinstance(p.get("price"), list) else p.get("price")
        if price_val:
          clean_val = str(price_val).replace(",", "").strip()
          num_match = re.search(r"(\d+(\.\d+)?)", clean_val)
          if num_match:
            return float(num_match.group(1))

    # Respaldo vía Expresión Regular directa si Next.js no trae la estructura estándar
    raw_prices = re.findall(r'"price"\s*:\s*\[?"?\s*(\d+(?:\.\d+)?)"?', html)
    if raw_prices:
      valid_prices = [float(p) for p in raw_prices if float(p) > 0]
      if valid_prices:
        return min(valid_prices)
  except Exception as e:
    print(f"Error en parsing avanzado de precio: {e}")

  return None


def check_prices():
  previous_data = load_previous_data()
  current_data = {}

  for product in PRODUCTS_TO_TRACK:
    prod_id = product["id"]
    prod_name = product["name"]
    prod_url = product["url"]

    print(f"Revisando producto: {prod_name}...")
    try:
      res = requests.get(prod_url, headers=HEADERS, timeout=30)
      print(f"Estado HTTP: {res.status_code}")

      if res.status_code == 200:
        soup_prod = BeautifulSoup(res.text, "html.parser")

        # Intentar extraer título
        title_el = soup_prod.select_one("h1")
        title = title_el.text.strip() if title_el else prod_name

        # Extracción avanzada de precio
        current_price = extract_price_from_next_data(res.text)

        # Respaldo HTML por selectores visuales clásicos en caso el JSON no responda
        if not current_price:
          price_el = soup_prod.select_one("span.copy-10, li.price-0, div.prices-0, [class*='price']")
          if price_el:
            clean_str = price_el.text.replace("S/", "").replace("$", "").replace(",", "").strip()
            num_match = re.search(r"(\d+(\.\d+)?)", clean_str)
            if num_match:
              current_price = float(num_match.group(1))

        print(f"Precio extraído: S/ {current_price}")

        if current_price:
          current_data[prod_id] = {
              "name": title,
              "price": current_price,
              "link": prod_url,
          }

          if prod_id in previous_data:
            old_price = previous_data[prod_id]["price"]
            print(f"Precio anterior: {old_price} | Precio actual: {current_price}")

            if current_price != old_price:
              diff = current_price - old_price
              if diff < 0:
                status_msg = "🎉 *¡BAJÓ DE PRECIO TU PRODUCTO, MI KING!* 💸📉\n¡Es el momento ideal!"
              else:
                status_msg = "⚠️ *¡ATENCIÓN MI KING: SUBIÓ DE PRECIO!* 📈🚀\nCuidado que encareció."

              msg = (
                  f"{status_msg}\n\n"
                  f"📦 *{title}*\n"
                  f"🔄 Antes: S/ {old_price:.2f}\n"
                  f"💲 Ahora: S/ {current_price:.2f}\n"
                  f"[🔗 Ver producto aquí]({prod_url})"
              )
              send_telegram_message(msg)
            else:
              print("El precio se mantiene igual respecto a la memoria.")
          else:
            print("Registrado por primera vez en memoria.")
        else:
          print(f"No se pudo determinar el precio para {prod_name}.")
      else:
        print(f"Error HTTP al revisar el producto: {res.status_code}")
    except Exception as e:
      print(f"Error técnico con el producto {prod_name}: {e}")

  if current_data:
    save_current_data(current_data)


if __name__ == "__main__":
  check_prices()
