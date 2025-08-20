from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/merhaba")
def merhaba():
    return "Merhaba! Render test başarılı 🎉"

if __name__ == "__main__":
    # Render için host='0.0.0.0' ve port ayarlayalım
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
