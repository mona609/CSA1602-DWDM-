"""RetailIQ - Online Retail Sales Forecasting and Customer Behavior Analytics.
Run locally:  python app.py   (then open http://127.0.0.1:5000)"""
import os, re, secrets, hmac, hashlib, sqlite3, smtplib, time, datetime as dt
from email.message import EmailMessage
from functools import wraps
import requests
from dotenv import load_dotenv
from flask import Flask, request, session, redirect, render_template, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()
app = Flask(__name__)
if not os.environ.get("SECRET_KEY"):
    print("WARNING: SECRET_KEY not set. Using a temporary key; logins reset on restart.")
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
    SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("PRODUCTION") == "1",
    PERMANENT_SESSION_LIFETIME=dt.timedelta(hours=8))
DB_PATH = os.environ.get("DB_PATH", "retailiq.db")
OTP_TTL, OTP_TRIES, RESEND_GAP, LOCK_FAILS, LOCK_SECS = 300, 3, 30, 5, 300


def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():  # runs at import, so it also works under gunicorn
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(email TEXT PRIMARY KEY,name TEXT,pw_hash TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS otps(ident TEXT PRIMARY KEY,h TEXT,expires REAL,tries INT,last_sent REAL);
        CREATE TABLE IF NOT EXISTS attempts(ident TEXT PRIMARY KEY,fails INT,locked_until REAL);""")


init_db()


def hash_otp(ident, otp):
    return hmac.new(app.config["SECRET_KEY"].encode(), f"{ident}:{otp}".encode(), hashlib.sha256).hexdigest()


# ---------- email ----------
def email_configured():
    return bool(os.environ.get("BREVO_API_KEY") or (os.environ.get("SENDER_EMAIL") and os.environ.get("SMTP_PASSWORD")))


def send_email(to, subject, body):
    sender = os.environ.get("SENDER_EMAIL", "")
    if os.environ.get("BREVO_API_KEY"):
        r = requests.post("https://api.brevo.com/v3/smtp/email", timeout=15,
                          headers={"api-key": os.environ["BREVO_API_KEY"], "accept": "application/json"},
                          json={"sender": {"email": sender, "name": "RetailIQ"}, "to": [{"email": to}],
                                "subject": subject, "textContent": body})
        if r.status_code >= 300:
            raise RuntimeError(f"Brevo error {r.status_code}: {r.text[:150]}")
        return
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = sender, to, subject
    m.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as s:
        s.login(sender, os.environ["SMTP_PASSWORD"])
        s.send_message(m)


# ---------- security ----------
@app.before_request
def csrf_guard():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    if request.method == "POST":
        if not hmac.compare_digest(request.headers.get("X-CSRF-Token", ""), session["csrf"]):
            return jsonify(ok=False, msg="Security token missing or expired. Refresh the page."), 400


@app.after_request
def headers(r):
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["X-Frame-Options"] = "DENY"
    r.headers["Referrer-Policy"] = "same-origin"
    r.headers["Content-Security-Policy"] = ("default-src 'self'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
                                            "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'")
    return r


@app.context_processor
def ctx():
    return dict(csrf=session.get("csrf", ""), user=session.get("user"), role=session.get("role"))


def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if not session.get("user"):
            if request.path.startswith("/api"):
                return jsonify(ok=False, msg="Please log in first."), 401
            return redirect("/login")
        return f(*a, **k)
    return w


def admin_required(f):
    @wraps(f)
    @login_required
    def w(*a, **k):
        if session.get("role") != "admin":
            return jsonify(ok=False, msg="Admin access only."), 403
        return f(*a, **k)
    return w


app.login_required, app.admin_required = login_required, admin_required


# ---------- auth ----------
def locked(ident):
    with db() as c:
        r = c.execute("SELECT * FROM attempts WHERE ident=?", (ident,)).fetchone()
    return int(r["locked_until"] - time.time()) if r and r["locked_until"] > time.time() else 0


def fail(ident):
    with db() as c:
        r = c.execute("SELECT fails FROM attempts WHERE ident=?", (ident,)).fetchone()
        n = (r["fails"] if r else 0) + 1
        until = time.time() + LOCK_SECS if n >= LOCK_FAILS else 0
        c.execute("REPLACE INTO attempts VALUES(?,?,?)", (ident, 0 if until else n, until))
    return LOCK_FAILS - n


def issue_otp(ident, to):
    otp = f"{secrets.randbelow(1000000):06d}"
    with db() as c:
        c.execute("REPLACE INTO otps VALUES(?,?,?,?,?)", (ident, hash_otp(ident, otp), time.time() + OTP_TTL, 0, time.time()))
    dev = None
    if email_configured():
        send_email(to, "Your RetailIQ verification code", f"Your OTP is {otp}. It is valid for 5 minutes.")
    else:
        print(f"[DEV] OTP for {ident}: {otp}")
        dev = otp
    return dev


@app.route("/")
def home():
    return redirect("/dashboard" if session.get("user") else "/login")


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.post("/api/register")
def register_api():
    d = request.get_json(silent=True) or {}
    name, email, pw = (d.get("name") or "").strip(), (d.get("email") or "").strip().lower(), d.get("password") or ""
    if len(name) < 2: return jsonify(ok=False, msg="Enter your full name.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email): return jsonify(ok=False, msg="Enter a valid email address.")
    if len(pw) < 8 or not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        return jsonify(ok=False, msg="Password needs 8+ characters with letters and numbers.")
    if pw != d.get("confirm"): return jsonify(ok=False, msg="Passwords do not match.")
    try:
        with db() as c:
            c.execute("INSERT INTO users VALUES(?,?,?,?)", (email, name, generate_password_hash(pw), dt.datetime.now().isoformat(timespec="seconds")))
    except sqlite3.IntegrityError:
        return jsonify(ok=False, msg="This email is already registered.")
    return jsonify(ok=True, msg="Account created. Please log in.")


@app.post("/api/login")
def login_api():
    d = request.get_json(silent=True) or {}
    role, ident, pw = d.get("role", "user"), (d.get("email") or "").strip().lower(), d.get("password") or ""
    left = locked(ident)
    if left: return jsonify(ok=False, msg=f"Account locked. Try again in {left // 60 + 1} minute(s).")
    if role == "admin":
        ap = os.environ.get("ADMIN_PASSWORD"), os.environ.get("ADMIN_EMAIL")
        if not all(ap): return jsonify(ok=False, msg="Admin login is not configured. Set ADMIN_PASSWORD and ADMIN_EMAIL in .env.")
        good, to, name = ident == "admin" and hmac.compare_digest(pw, ap[0]), ap[1], "Admin"
    else:
        with db() as c:
            u = c.execute("SELECT * FROM users WHERE email=?", (ident,)).fetchone()
        good, to, name = bool(u) and check_password_hash(u["pw_hash"], pw), ident, (u["name"] if u else "")
    if not good:
        rem = fail(ident)
        return jsonify(ok=False, msg="Account locked for 5 minutes." if rem <= 0 else f"Wrong email or password. {rem} tries left.")
    try:
        dev = issue_otp(ident, to)
    except Exception as e:
        return jsonify(ok=False, msg=f"Could not send the OTP email: {e}")
    session["pending"] = dict(ident=ident, role=role, name=name, to=to)
    with db() as c: c.execute("DELETE FROM attempts WHERE ident=?", (ident,))
    return jsonify(ok=True, msg=f"OTP sent to {to}." if not dev else "Email is not configured, so the OTP is shown below (development mode).", dev_otp=dev)


@app.post("/api/resend")
def resend_api():
    p = session.get("pending")
    if not p: return jsonify(ok=False, msg="Start again from the login page.")
    with db() as c:
        r = c.execute("SELECT last_sent FROM otps WHERE ident=?", (p["ident"],)).fetchone()
    if r and time.time() - r["last_sent"] < RESEND_GAP:
        return jsonify(ok=False, msg=f"Wait {int(RESEND_GAP - (time.time() - r['last_sent'])) + 1}s before resending.")
    try: dev = issue_otp(p["ident"], p["to"])
    except Exception as e: return jsonify(ok=False, msg=f"Could not send the OTP email: {e}")
    return jsonify(ok=True, msg="A new OTP was sent.", dev_otp=dev)


@app.post("/api/verify")
def verify_api():
    p = session.get("pending")
    if not p: return jsonify(status="failed", msg="Verification failed. Please log in again.")
    otp = ((request.get_json(silent=True) or {}).get("otp") or "").strip()
    with db() as c:
        r = c.execute("SELECT * FROM otps WHERE ident=?", (p["ident"],)).fetchone()
        if not r: return jsonify(status="failed", msg="Verification failed. Please log in again.")
        if time.time() > r["expires"]: return jsonify(status="expired", msg="OTP expired. Please resend.")
        if r["tries"] >= OTP_TRIES:
            c.execute("DELETE FROM otps WHERE ident=?", (p["ident"],))
            return jsonify(status="failed", msg="Too many wrong tries. Please log in again.")
        if not hmac.compare_digest(r["h"], hash_otp(p["ident"], otp)):
            c.execute("UPDATE otps SET tries=tries+1 WHERE ident=?", (p["ident"],))
            left = OTP_TRIES - r["tries"] - 1
            return jsonify(status="wrong" if left > 0 else "failed", msg=f"Wrong OTP. {left} tries left." if left > 0 else "Too many wrong tries. Please log in again.")
        c.execute("DELETE FROM otps WHERE ident=?", (p["ident"],))
    session.clear(); session.permanent = True
    session.update(user=p["name"] or p["ident"], role=p["role"], csrf=secrets.token_hex(16))
    return jsonify(status="success", msg="Login Successful")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", active="dashboard")


import phase2, phase3, phase5, phase6  # noqa: E402
for m in (phase2, phase3, phase5, phase6):
    m.register(app)

if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
