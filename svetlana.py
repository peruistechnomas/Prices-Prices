import json
import os
import re
import time
from bs4 import BeautifulSoup
import requests

TOKEN = "8877774720:AAEvlIkejUrYW1wZNcwf95o0dm_LxWhW0Iw"
CHAT_ID = "1301227407"


def enviar_alerta(mensaje):
  url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
  payload = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
  try:
    requests.post(url, data=payload)
  except Exception as e:
    print(f"Error al enviar mensaje: {e}")


# --- MENSAJE DE PRUEBA ---
enviar_alerta("🤖 ¡Hola! Mensaje de prueba de Svetlana funcionando al 100%.")

productos = [
    {
        "id": "falabella_lamartina",
        "nombre": "Chompa Hombre La Martina (Falabella)",
        "url": (
            "https://www.falabella.com.pe/falabella-pe/product/21414094/chompa-hombre-la-martina/21414101"
        ),
        "tienda": "falabella",
    },
    {
        "id": "ripley_marquis",
        "nombre": "Polo Manga Corta Algodón Marquis (Ripley)",
        "url": (
            "https://simple.ripley.com.pe/polo-manga-corta-algodon-hombre-marquis-2005373327929?color_80=cafe&s=mdco&pos=26&catPos=74&p=2&ps=48&redirectType=redirection_term-catalog&prodNavFullCategory=marquis_casual_homb&searchTerm=marquis%20hombre"
        ),
        "tienda": "ripley",
    },
    {
        "id": "ripley_spavaldi_beata",
        "nombre": "Casaca Hombre Spavaldi Beata (Ripley)",
        "url": (
            "https://simple.ripley.com.pe/casaca-hombre-spavaldi-beata-2005370113310?color_80=Caf%C3%A9&s=mdco&pos=15&catPos=15&p=1&ps=39&orig=PSP&searchTerm=SPAVALDI"
        ),
        "tienda": "ripley",
    },
    {
        "id": "ripley_spavaldi_ezio",
        "nombre": "Pantalón Hombre Spavaldi Ezio (Ripley)",
        "url": (
            "https://simple.ripley.com.pe/pantalon-hombre-spavaldi-ezio-2005364407890?color_80=Arena&s=mdco&pos=10&catPos=10&p=1&ps=39&orig=PSP&searchTerm=SPAVALDI"
        ),
        "tienda": "ripley",
    },
]

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

precios_guardados = {}
if os.path.exists("precios.json"):
  try:
    with open("precios.json", "r") as f:
      precios_guardados = json.load(f)
  except:
    pass

for item in productos:
  try:
    response = requests.get(item["url"], headers=headers, timeout=15)
    if response.status_code == 200:
      soup = BeautifulSoup(response.text, "html.parser")
      precio_actual = None

      if item["tienda"] == "falabella":
        tag_precio = soup.find(
            "span", {"class": lambda x: x and "precio" in x.lower()}
        )
        if not tag_precio:
          tag_precio = soup.find(
              "li", {"class": lambda x: x and "price" in x.lower()}
          )
        if tag_precio:
          precio_actual = tag_precio.get_text(strip=True)

      elif item["tienda"] == "ripley":
        tag_precio = soup.find(
            "li", {"class": lambda x: x and "card-price" in x.lower()}
        )
        if not tag_precio:
          tag_precio = soup.find(
              "li", {"class": lambda x: x and "offer-price" in x.lower()}
          )
        if not tag_precio:
          tag_precio = soup.find(
              "div", {"class": lambda x: x and "product-price" in x.lower()}
          )
        if not tag_precio:
          posibles = soup.find_all(
              ["span", "div", "li"],
              {"class": lambda x: x and "price" in x.lower()},
          )
          for p in posibles:
            txt = p.get_text(strip=True)
            if "S/" in txt or "s/" in txt:
              precio_actual = txt
              break

        if tag_precio:
          precio_actual = tag_precio.get_text(strip=True)

      if precio_actual:
        nums = re.findall(r"\d{2,4}\.\d{2}", precio_actual)
        if not nums:
          nums = re.findall(r"\d{2,4}", precio_actual)
        precio_limpio = (
            nums[-1]
            if nums
            else "".join(c for c in precio_actual if c.isdigit() or c == ".")
        )

        prod_id = item["id"]
        precio_anterior = precios_guardados.get(prod_id)

        if precio_anterior is None:
          precios_guardados[prod_id] = precio_limpio
          print(f"[Inicializado] {item['nombre']}: S/ {precio_limpio}")
        elif precio_anterior != precio_limpio:
          mensaje = (
              f"🚨 *¡CAMBIO DE PRECIO DETECTADO!* 🚨\n\n"
              f"📦 *Producto:* {item['nombre']}\n"
              f"📉 *Precio anterior:* S/ {precio_anterior}\n"
              f"📈 *Precio actual:* S/ {precio_limpio}\n\n"
              f"🔗 [Ver producto]({item['url']})"
          )
          enviar_alerta(mensaje)
          precios_guardados[prod_id] = precio_limpio

    time.sleep(3)
  except Exception as e:
    print(f"Error revisando {item['nombre']}: {e}")

with open("precios.json", "w") as f:
  json.dump(precios_guardados, f, indent=4)
