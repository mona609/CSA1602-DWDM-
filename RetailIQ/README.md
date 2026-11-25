# RetailIQ - Online Retail Sales Forecasting and Customer Behavior Analytics

## Run locally
1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill it in (at least SECRET_KEY, ADMIN_PASSWORD, ADMIN_EMAIL).
3. `python app.py`  then open http://127.0.0.1:5000

The dataset `amazon_sales_data_2025_csv.xlsx` must stay in this folder.

## Login / OTP
- Register a user, then log in with User. Admin: choose Admin, username `admin`, password = ADMIN_PASSWORD.
- If no email settings are filled in, the OTP is printed in the terminal AND shown on the OTP screen
  (development mode) so you can demo without email. With SENDER_EMAIL + SMTP_PASSWORD (Gmail App Password)
  or BREVO_API_KEY set, the OTP is emailed instead.

## Pages
Dashboard, Dataset & ETL, Star & Snowflake Schema, 3D OLAP Cube, Analytics (chart builder),
Prediction (weekly forecast), Report (PDF, charts only), Manage Users & Data (admin only).

## Deploy on Render
- Build: `pip install -r requirements.txt`
- Start: `gunicorn app:app --workers 1 --threads 4 --timeout 120`
- Env vars: SECRET_KEY, ADMIN_PASSWORD, ADMIN_EMAIL, SENDER_EMAIL, BREVO_API_KEY, DB_PATH, PRODUCTION=1, PYTHON_VERSION
- Use a persistent disk (set DB_PATH to a path on it) or users are lost when Render restarts.
- Charts and the 3D cube load Chart.js / Three.js from cdnjs, so the browser needs internet.
