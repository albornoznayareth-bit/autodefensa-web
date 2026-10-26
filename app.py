import os
# Cargar .env.local solo para pruebas locales.
if os.environ.get("VERCEL") != "1":
    archivo_env = os.path.join(os.path.dirname(__file__), ".env.local")
    if os.path.isfile(archivo_env):
        with open(archivo_env, encoding="utf-8") as archivo:
            for linea in archivo:
                linea = linea.strip()
                if not linea or linea.startswith("#") or "=" not in linea:
                    continue
                clave, valor = linea.split("=", 1)
                clave = clave.strip()
                valor = valor.strip().strip('"').strip("'")
                os.environ.setdefault(clave, valor)
import html
import urllib.request
import urllib.error
from urllib.parse import urlparse, urljoin
from html.parser import HTMLParser
from flask import Flask, render_template, send_from_directory, request, jsonify

# Los archivos estáticos se publican desde public/ en Vercel.
# Esta ruta también permite probarlos en el entorno local.
app = Flask(__name__, static_folder=None)


@app.route("/")
def inicio():
    return render_template(
        "index.html",
        supabase_url=os.environ.get("SUPABASE_URL", ""),
        supabase_key=os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")
    )


@app.route("/static/<path:filename>", endpoint="static")
def archivos_estaticos(filename):
    return send_from_directory("public/static", filename)


@app.route("/robots.txt")
def robots():
    return send_from_directory("public", "robots.txt")


@app.route("/google6edb0130f974bf09.html")
def google_verificacion():
    return send_from_directory("public", "google6edb0130f974bf09.html")


@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory("public", "sitemap.xml")




@app.route("/admin")
def admin():
    return render_template(
        "admin.html",
        supabase_url=os.environ.get("SUPABASE_URL", ""),
        supabase_key=os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")
    )



# --- Extractor seguro de metadatos de ticketeras ---

DOMINIOS_PERMITIDOS = ("portaldisc.com", "passline.com", "puntoticket.com")


def url_permitida(url):
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        return (
            parsed.scheme == "https"
            and parsed.username is None
            and parsed.password is None
            and any(host == d or host.endswith("." + d)
                    for d in DOMINIOS_PERMITIDOS)
            and parsed.port in (None, 443)
        )
    except ValueError:
        return False


class RedireccionesSeguras(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        destino = urljoin(req.full_url, newurl)
        if not url_permitida(destino):
            raise urllib.error.URLError(
                "La página intentó redirigir a un dominio no permitido."
            )
        return super().redirect_request(
            req, fp, code, msg, headers, destino
        )


class LectorMetadatos(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.metas = {}
        self.title = []
        self.en_title = False

    def handle_starttag(self, tag, attrs):
        attrs = {k.lower(): v for k, v in attrs if k}
        if tag.lower() == "meta":
            key = (attrs.get("property") or attrs.get("name") or "").lower()
            value = attrs.get("content")
            if key and value and key not in self.metas:
                self.metas[key] = value.strip()
        elif tag.lower() == "title":
            self.en_title = True

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.en_title = False

    def handle_data(self, data):
        if self.en_title:
            self.title.append(data)


@app.route("/api/extract-event", methods=["POST"])
def extraer_evento():
    datos = request.get_json(silent=True) or {}
    url = (datos.get("url") or "").strip()

    if not url or len(url) > 2048 or not url_permitida(url):
        return jsonify({
            "ok": False,
            "error": "Introduce un enlace HTTPS válido de PortalDisc, Passline o PuntoTicket."
        }), 400

    try:
        opener = urllib.request.build_opener(RedireccionesSeguras())
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AutodefensaEventReader/1.0)",
                     "Accept": "text/html"}
        )
        with opener.open(req, timeout=12) as response:
            final_url = response.geturl()
            if not url_permitida(final_url):
                return jsonify({
                    "ok": False,
                    "error": "La página final no pertenece a una ticketera permitida."
                }), 400
            content_type = response.headers.get_content_type()
            if content_type != "text/html":
                return jsonify({
                    "ok": False,
                    "error": "El enlace no devolvió una página HTML."
                }), 422
            charset = response.headers.get_content_charset() or "utf-8"
            contenido = response.read(2_000_001)

        if len(contenido) > 2_000_000:
            return jsonify({
                "ok": False,
                "error": "La página supera el tamaño máximo permitido."
            }), 413

        pagina = contenido.decode(charset, errors="replace")

        lector = LectorMetadatos()
        lector.feed(pagina)
        metas = lector.metas

        titulo = (
            metas.get("og:title")
            or metas.get("twitter:title")
            or " ".join(lector.title).strip()
        )
        descripcion = (
            metas.get("og:description")
            or metas.get("description")
            or metas.get("twitter:description")
            or ""
        )
        imagen = metas.get("og:image") or metas.get("twitter:image") or ""
        imagen = urljoin(final_url, html.unescape(imagen)) if imagen else ""

        # Una URL que termina en una carpeta no se considera un afiche confirmado.
        imagen_valida = bool(
            imagen
            and url_permitida(imagen)
            and not urlparse(imagen).path.endswith("/")
            and urlparse(imagen).path.lower().endswith(
                (".jpg", ".jpeg", ".png", ".webp", ".avif")
            )
        )

        resultado = {
            "ok": True,
            "url": final_url,
            "titulo": html.unescape(titulo).strip(),
            "descripcion": html.unescape(descripcion).strip(),
            "imagen": imagen if imagen_valida else "",
            "imagen_detectada": imagen,
            "imagen_valida": imagen_valida,
            "fecha": "",
            "hora": "",
            "lugar": "",
            "direccion": "",
            "precio": "",
            "pendientes": []
        }

        for campo in ("titulo", "fecha", "hora", "lugar", "direccion", "precio"):
            if not resultado[campo]:
                resultado["pendientes"].append(campo)

        if not imagen_valida:
            resultado["pendientes"].append("imagen")

        return jsonify(resultado)

    except Exception as error:
        app.logger.warning("No se pudo extraer el evento: %s", error)
        return jsonify({
            "ok": False,
            "error": "No pudimos leer esta página. Puedes completar los datos manualmente."
        }), 502



@app.route("/terminos")
def pagina_terminos():
    return render_template("terminos.html")


@app.route("/privacidad")
def pagina_privacidad():
    return render_template("privacidad.html")


@app.route("/cookies")
def pagina_cookies():
    return render_template("cookies.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
