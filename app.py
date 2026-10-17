import os
from flask import Flask, render_template, send_from_directory

# Los archivos estáticos se publican desde public/ en Vercel.
# Esta ruta también permite probarlos en el entorno local.
app = Flask(__name__, static_folder=None)


@app.route("/")
def inicio():
    return render_template("index.html")


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
