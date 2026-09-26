from flask import Flask, render_template, send_from_directory

app = Flask(__name__)


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/robots.txt")
def robots():
    return send_from_directory("static", "robots.txt")


@app.route("/google6edb0130f974bf09.html")
def google_verificacion():
    return send_from_directory(".", "google6edb0130f974bf09.html")


@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory("static", "sitemap.xml")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
