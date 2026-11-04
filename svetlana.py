import json
import os
import re
import requests
from bs4 import BeautifulSoup

# ==========================================
# 1. ENLACES DE MARCAS Y CATEGORÍAS (Múltiples productos)
# ==========================================
CATEGORIES_TO_TRACK = [
    {
        "id": "la_martina_page2",
        "name": "La Martina (Página 2)",
        "url": "https://www.falabella.com.pe/falabella-pe/brand/LA%20MARTINA?latLong=%257B%2522latitude%2522%253A%2522-12.086940304221134%2522%252C%2522longitude%2522%253A%2522-76.98159624185517%2522%257D&sortBy=derived.price.search%2Casc&page=2",
    },
    {
        "id": "polo_ralph_lauren",
        "name": "Polo Ralph Lauren",
        "url": "https://www.falabella.com.pe/falabella-pe/brand/POLO%20RALPH%20LAUREN",
    },
]

# ==========================================
# 2. TU PRODUCTO ESPECÍFICO (Seguimiento directo)
# ==========================================
SPECIFIC_PRODUCT = {
    "id": "chompa_estrella_la_martina",
    "name": "Chompa Hombre La Martina (Específica)",
    "url": "https://www.falabella.com.pe/falabella-pe/product/21414094/chompa-hombre-la-martina/21414099",
}

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9",
}

DATA_FILE = "last_prices.json"


def load_previous_data():
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return {}
  return {}


def save_current_data(data):
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


def send_telegram_message(message):
  if not TELEGRAM_TOKEN or not CHAT_ID:
    print("Credenciales de Telegram no configuradas.")
    return
  url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
  payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
  try:
    requests.post(url, json=payload, timeout=30)
  except Exception as e:
    print(f"Error al enviar mensaje a Telegram: {e}")


def parse_price(price_str):
  if not price_str:
    return None
  clean_str = (
      price_str.replace("S/", "")
      .replace("$", "")
      .replace(",", "")
      .strip()
  )
  match = re.search(r"(\d+(\.\d+)?)", clean_str)
  if match:
    return float(match.group(1))
  return None


def check_prices():
  previous_data = load_previous_data()
  current_data = {}

  # ----------------------------------------------------
  # PROCESAR CATEGORÍAS Y MARCAS (Múltiples productos)
  # ----------------------------------------------------
  for item in CATEGORIES_TO_TRACK:
    item_id_prefix = item["id"]
    item_name = item["name"]
    url = item["url"]

    print(f"Analizando categoría: {item_name}...")

    try:
      response = requests.get(url, headers=HEADERS, timeout=30)
      if response.status_code != 200:
        print(f"Error HTTP {response.status_code} para {item_name}")
        continue

      soup = BeautifulSoup(response.text, "html.parser")
      products = soup.select(
          "div.search-results-item, div.jsx-3243929427, article.pod-item"
      )
      if not products:
        products = soup.select(".pod-item")

      print(f"Encontrados {len(products)} productos en {item_name}.")

      for index, prod in enumerate(products):
        try:
          title_elem = prod.select_one(
              "b.pod-subTitle, a.pod-link, .pod-title"
          )
          title = (
              title_elem.text.strip()
              if title_elem
              else f"Producto {index} - {item_name}"
          )

          link_elem = prod.select_one("a.pod-link")
          link = link_elem["href"] if link_elem and "href" in link_elem else url

          price_elem = prod.select_one(
              "li.price-0, span.copy-10, .pod-prices .copy-2"
          )
          price_text = price_elem.text if price_elem else None
          current_price = parse_price(price_text)

          if not current_price:
            continue

          unique_key = f"{item_id_prefix}_{index}"
          current_data[unique_key] = {
              "name": title,
              "price": current_price,
              "link": link,
          }

          if unique_key in previous_data:
            old_price = previous_data[unique_key]["price"]
            if current_price != old_price:
              diff = current_price - old_price
              if diff < 0:
                status_msg = (
                    "🎉 *¡BAJÓ DE PRECIO, MI KING!* 💸📉\n¡Aprovecha que está"
                    " más barato!"
                )
              else:
                status_msg = (
                    "⚠️ *¡ATENCIÓN MI KING: SUBIÓ DE PRECIO!* 📈🚀\nSe puso un"
                    " poco más costoso..."
                )

              msg = (
                  f"{status_msg}\n\n"
                  f"📦 *{title}*\n"
                  f"🔄 Antes: S/ {old_price:.2f}\n"
                  f"💲 Ahora: S/ {current_price:.2f}\n"
                  f"[🔗 Ver producto aquí]({link})"
              )
              send_telegram_message(msg)

        except Exception as inner_e:
          print(f"Error procesando producto en categoría: {inner_e}")

    except Exception as e:
      print(f"Error técnico conectando a {item_name}: {e}")

  # ----------------------------------------------------
  # PROCESAR TU PRODUCTO ESPECÍFICO (Seguimiento directo)
  # ----------------------------------------------------
  print(f"Analizando producto específico: {SPECIFIC_PRODUCT['name']}...")
  try:
    res = requests.get(SPECIFIC_PRODUCT["url"], headers=HEADERS, timeout=30)
    if res.status_code == 200:
      soup_prod = BeautifulSoup(res.text, "html.parser")

      title_el = soup_prod.select_one("h1.product-title, span.wy-product-title")
      prod_title = (
          title_el.text.strip()
          if title_el
          else SPECIFIC_PRODUCT["name"]
      )

      price_el = soup_prod.select_one(
          "li.price-0, span.copy-10, .product-prices price"
      )
      price_text = price_el.text if price_el else None
      current_price = parse_price(price_text)

      if current_price:
        unique_key = SPECIFIC_PRODUCT["id"]
        current_data[unique_key] = {
            "name": prod_title,
            "price": current_price,
            "link": SPECIFIC_PRODUCT["url"],
        }

        if unique_key in previous_data:
          old_price = previous_data[unique_key]["price"]
          if current_price != old_price:
            diff = current_price - old_price
            if diff < 0:
              status_msg = (
                  "🎉 *¡BAJÓ DE PRECIO TU PRODUCTO FAVORITO, MI KING!* 💸📉\n¡Es"
                  " el momento ideal!"
              )
            else:
              status_msg = (
                  "⚠️ *¡ATENCIÓN MI KING: SUBIÓ TU PRODUCTO!* 📈🚀\nCuidado que"
                  " encareció."
              )

            msg = (
                f"{status_msg}\n\n"
                f"📦 *{prod_title}*\n"
                f"🔄 Antes: S/ {old_price:.2f}\n"
                f"💲 Ahora: S/ {current_price:.2f}\n"
                f"[🔗 Ver chompa aquí]({SPECIFIC_PRODUCT['url']})"
            )
            send_telegram_message(msg)
    else:
      print(f"Error HTTP al revisar la chompa específica: {res.status_code}")
  except Exception as e:
    print(f"Error técnico con el producto específico: {e}")

  # Guardar todo en el JSON
  if current_data:
    save_current_data(current_data)


if __name__ == "__main__":
  check_prices()
