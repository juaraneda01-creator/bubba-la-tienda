#!/usr/bin/env python3
"""Genera la copia pública de la tienda Bubba L.A. a partir de la página en vivo.

Uso: python3 sync.py RUTA_DEL_HTML_EN_VIVO
Escribe index.html en esta carpeta (logo.jpg ya está en el repositorio). Termina con error (código 1) si
alguna verificación falla; en ese caso no se debe subir nada.

Qué hace:
- Quita el libro de ventas cifrado y los costos de los productos.
- Pone el link público (Netlify) como link para compartir.
- Agrega la vista previa para WhatsApp/Instagram (título, descripción, logo).
"""
import json, re, sys
from pathlib import Path

PUBLIC_URL = "https://bubba-la-tienda.netlify.app"
TITLE = "Bubba L.A. · Detallitos Sorpresas"
DESC = "Arma tu detallito sorpresa: ramos, globos, cosmética y accesorios. Cotiza al instante y envía tu pedido por WhatsApp."
HERE = Path(__file__).parent
RX = re.compile(r'(<script id="state" type="application/json">)(.*?)(</script>)', re.S)
MARK_A, MARK_B = "<!-- vista-previa -->", "<!-- /vista-previa -->"


def fail(msg):
    print("ERROR:", msg)
    sys.exit(1)


def main(src):
    h = Path(src).read_text(encoding="utf-8")
    m = RX.search(h)
    if not m:
        fail("no se encontró el bloque de estado en la página en vivo")
    st = json.loads(m.group(2))
    if not st.get("productos"):
        fail("la página en vivo no trae productos")

    # 1) datos privados fuera
    st["libro"] = None
    for p in st["productos"]:
        p["k"] = None
    # 2) link para compartir = link público
    st.setdefault("negocio", {})["link"] = PUBLIC_URL
    data = json.dumps(st, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    pub = h[: m.start(2)] + data + h[m.end(2):]

    # 3) logo para la vista previa: logo.jpg ya está en esta carpeta (600x600, formato que WhatsApp acepta)
    image = f"{PUBLIC_URL}/logo.jpg" if (HERE / "logo.jpg").exists() else ""

    # 4) vista previa al compartir
    pub = re.sub(re.escape(MARK_A) + ".*?" + re.escape(MARK_B) + r"\n?", "", pub, flags=re.S)
    tags = [
        f'<meta name="description" content="{DESC}">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:url" content="{PUBLIC_URL}/">',
        f'<meta property="og:title" content="{TITLE}">',
        f'<meta property="og:description" content="{DESC}">',
        '<meta property="og:locale" content="es_CL">',
        '<meta name="twitter:card" content="summary">',
    ]
    if image:
        tags += [f'<meta property="og:image" content="{image}">', f'<link rel="icon" href="{image}">']
    block = MARK_A + "\n" + "\n".join(tags) + "\n" + MARK_B + "\n"
    if "</title>\n" not in pub:
        fail("no se encontró el título de la página")
    pub = pub.replace("</title>\n", "</title>\n" + block, 1)

    # 5) verificaciones antes de escribir
    # la etiqueta también aparece una vez dentro del código de la página (como texto), por eso se cuenta al inicio de línea
    if len(re.findall(r'^<script id="state" type="application/json">', pub, re.M)) != 1:
        fail("el bloque de estado quedó duplicado")
    chk = json.loads(RX.search(pub).group(2))
    if chk.get("libro") is not None:
        fail("el libro de ventas sigue presente")
    if any(p.get("k") is not None for p in chk["productos"]):
        fail("quedaron costos en la copia pública")
    if chk["negocio"].get("link") != PUBLIC_URL:
        fail("el link para compartir no es el público")
    if len(chk["productos"]) != len(st["productos"]):
        fail("cambió la cantidad de productos")

    (HERE / "index.html").write_text(pub, encoding="utf-8")
    vis = sum(1 for p in chk["productos"] if p.get("v") is not False)
    print(f"OK: {len(chk['productos'])} productos ({vis} visibles), sin libro ni costos, link {PUBLIC_URL}, vista previa {'con' if image else 'sin'} logo")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        fail("uso: python3 sync.py RUTA_DEL_HTML_EN_VIVO")
    main(sys.argv[1])
