"""Prediction: weekly sales forecast."""
import numpy as np
from flask import render_template, jsonify, request
import pandas as pd
import phase2


def register(app):
    L = app.login_required

    @app.route("/prediction")
    @L
    def prediction_page(): return render_template("prediction.html", active="prediction")

    @app.get("/api/forecast")
    @L
    def forecast():
        a = request.args
        weeks, method = min(12, max(1, a.get("weeks", 4, int))), a.get("method", "linear")
        df = phase2.get_df()
        df = df[df["Status"] == "Completed"]
        for key in ("Category", "Product"):
            if a.get(key.lower()) and a.get(key.lower()) != "All": df = df[df[key] == a.get(key.lower())]
        if df.empty: return jsonify(ok=False, msg="No completed orders for that filter."), 400
        w = df.set_index("Date")["Total Sales"].resample("W-SUN").sum()
        if len(w) > 4: w = w.iloc[1:-1]  # drop partial first and last weeks
        if len(w) < 3: return jsonify(ok=False, msg="Not enough weekly data to forecast."), 400
        v, n = w.values.astype(float), len(w)
        if method == "ma":
            f = [float(v[-3:].mean())] * weeks
            slope = 0.0
        else:
            slope, icpt = np.polyfit(np.arange(n), v, 1)
            f = [max(0.0, float(slope * (n + i) + icpt)) for i in range(weeks)]
        fut = [(w.index[-1] + pd.Timedelta(weeks=i + 1)).strftime("%d %b") for i in range(weeks)]
        mae = float(np.mean(np.abs(v - (np.polyval(np.polyfit(np.arange(n), v, 1), np.arange(n)) if method != "ma" else np.convolve(v, np.ones(3) / 3, "same")))))
        return jsonify(ok=True, labels=[x.strftime("%d %b") for x in w.index], actual=[round(float(x)) for x in v],
                       future_labels=fut, forecast=[round(x) for x in f], slope=round(float(slope)), weeks_used=n, mae=round(mae),
                       categories=sorted(phase2.get_df()["Category"].unique().tolist()),
                       products=sorted(phase2.get_df()["Product"].unique().tolist()))
