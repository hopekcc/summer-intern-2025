import os, requests
from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
from dotenv import load_dotenv

load_dotenv()                     # reads .env
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
BACKEND_URL   = os.getenv("BACKEND_URL")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form["email"]
        password = request.form["password"]

        # 1) Call FastAPI /login (which uses Firebase under the hood)
        resp = requests.post(
            f"{BACKEND_URL}/login",
            json={"email": email, "password": password}
        )

        if resp.ok:
            data = resp.json()
            session["idToken"]    = data["idToken"]
            session["user_email"] = email
            return redirect(url_for("home"))
        else:
            flash(resp.json().get("detail", "Login failed"))
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route('/')
def home():
    return render_template('home.html', username='Ryan', insert_text='Wish you have a good day!!!')

if __name__ == '__main__':
    app.run(debug=True)
