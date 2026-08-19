#!/usr/bin/env python3
"""
Bot que revisa la cartelera de "Ofertas ALE y Optativas" de la Facultad de
Ciencias Económicas (UNICEN, Tandil) y avisa por Gmail cuando aparece una
oferta nueva (materia optativa, ALE, etc.).

Fuente: https://www.econ.unicen.edu.ar/alumnos/ale/ofertas-ale-y-optativas

Cómo funciona:
1. Descarga todas las páginas del listado (paginado por ?page=N).
2. Extrae cada oferta: código (ej. MO237), título, y el resto del texto del
   bloque (para sacar fechas de inscripción, cupos, etc. si están).
3. Compara los códigos encontrados contra los que ya vio antes
   (guardados en seen_ofertas.json).
4. Si hay códigos nuevos, manda un mail a Gmail con el detalle.
5. Guarda el nuevo estado en seen_ofertas.json (se commitea de vuelta
   al repo desde el workflow de GitHub Actions).

Variables de entorno esperadas (se configuran como Secrets en GitHub):
  GMAIL_USER          -> tu dirección de Gmail que envía el mail
  GMAIL_APP_PASSWORD  -> contraseña de aplicación de Gmail (NO tu contraseña normal)
  GMAIL_TO            -> a qué dirección mandar el aviso (puede ser la misma GMAIL_USER)
  KEYWORDS (opcional) -> lista separada por comas para filtrar solo ciertas ofertas,
                          ej: "Materia Optativa" para avisar solo de optativas y no de ALE.
                          Si no se define, avisa de TODO lo nuevo.
"""

import os
import re
import json
import smtplib
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.econ.unicen.edu.ar/alumnos/ale/ofertas-ale-y-optativas"
STATE_FILE = os.path.join(os.path.dirname(__file__), "seen_ofertas.json")
MAX_PAGES = 15  # límite de seguridad para no scrapear infinito

# Un código de oferta se ve como "AD178", "MO237", "TA232", "AE27", "CO256"
CODE_RE = re.compile(r"^[A-Z]{2,4}\d{1,4}$")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CarteleraBot/1.0; +personal use)"
}


def fetch_page_text(page: int) -> str:
    """Descarga una página del listado y devuelve el texto visible, en orden."""
    url = BASE_URL if page == 0 else f"{BASE_URL}?page={page}"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Nos quedamos con el contenido principal para evitar ruido de header/footer
    main = soup.find("main") or soup.find(id="main-content") or soup
    return main.get_text(separator="\n")


def parse_offers(text: str) -> dict:
    """
    Parsea el texto plano de la página y devuelve un dict:
      { codigo: {"titulo": ..., "detalle": ...} }
    """
    lines = [l.strip() for l in text.split("\n")]
    lines = [l for l in lines if l]  # sacamos líneas vacías

    offers = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if CODE_RE.match(line):
            code = line
            # el título es la próxima línea no vacía
            titulo = lines[i + 1] if i + 1 < len(lines) else "(sin título)"

            # juntamos algunas líneas siguientes como "detalle" para el mail,
            # cortando si aparece otro código (= empieza la próxima oferta)
            detalle_lines = []
            j = i + 2
            while j < len(lines) and not CODE_RE.match(lines[j]) and len(detalle_lines) < 12:
                detalle_lines.append(lines[j])
                j += 1

            offers[code] = {
                "titulo": titulo,
                "detalle": " | ".join(detalle_lines[:6]),
            }
        i += 1
    return offers


def fetch_all_offers() -> dict:
    all_offers = {}
    for page in range(MAX_PAGES):
        try:
            text = fetch_page_text(page)
        except requests.RequestException as e:
            print(f"[WARN] no se pudo descargar la página {page}: {e}", file=sys.stderr)
            break

        page_offers = parse_offers(text)
        if not page_offers:
            # no hay más ofertas => se acabaron las páginas
            break

        all_offers.update(page_offers)

        # Si el sitio no tiene link a "página siguiente", cortamos
        if "Siguiente página" not in text and page > 0:
            break

    return all_offers


def load_seen() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_seen(offers: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(offers, f, ensure_ascii=False, indent=2, sort_keys=True)


def matches_keywords(titulo: str, keywords: list[str]) -> bool:
    if not keywords:
        return True
    titulo_low = titulo.lower()
    return any(kw.strip().lower() in titulo_low for kw in keywords if kw.strip())


def send_email(new_offers: dict) -> None:
    gmail_user = os.environ["GMAIL_USER"]
    gmail_pass = os.environ["GMAIL_APP_PASSWORD"]
    gmail_to = os.environ.get("GMAIL_TO", gmail_user)

    subject = f"📚 {len(new_offers)} oferta(s) nueva(s) en la cartelera ALE/Optativas"

    body_lines = [
        "Se detectaron nuevas ofertas en la cartelera de la Facultad:",
        BASE_URL,
        "",
    ]
    for code, data in new_offers.items():
        body_lines.append(f"• [{code}] {data['titulo']}")
        if data.get("detalle"):
            body_lines.append(f"   {data['detalle']}")
        body_lines.append("")

    body_lines.append("Andá a SIU Guaraní a inscribirte antes de que se llene el cupo.")

    msg = MIMEMultipart()
    msg["From"] = gmail_user
    msg["To"] = gmail_to
    msg["Subject"] = subject
    msg.attach(MIMEText("\n".join(body_lines), "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_pass)
        server.sendmail(gmail_user, [gmail_to], msg.as_string())

    print(f"Mail enviado a {gmail_to} avisando de {len(new_offers)} oferta(s) nueva(s).")


def main():
    keywords_env = os.environ.get("KEYWORDS", "")
    keywords = [k for k in keywords_env.split(",") if k.strip()]

    print("Descargando cartelera...")
    current_offers = fetch_all_offers()
    print(f"Ofertas encontradas en la web: {len(current_offers)}")

    seen_offers = load_seen()

    new_codes = [c for c in current_offers if c not in seen_offers]
    new_offers = {c: current_offers[c] for c in new_codes}

    if keywords:
        new_offers = {
            c: d for c, d in new_offers.items() if matches_keywords(d["titulo"], keywords)
        }

    if new_offers:
        print(f"¡Hay {len(new_offers)} oferta(s) nueva(s)! Enviando mail...")
        for c, d in new_offers.items():
            print(f"  - [{c}] {d['titulo']}")
        send_email(new_offers)
    else:
        print("No hay ofertas nuevas que avisar.")

    # Guardamos TODAS las ofertas vistas (no solo las filtradas por keywords)
    # para no perder de vista códigos aunque no matcheen el filtro.
    save_seen(current_offers)


if __name__ == "__main__":
    main()
