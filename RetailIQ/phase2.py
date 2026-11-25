"""Dataset, ETL, schema, OLAP cube and analytics APIs."""
import os, glob, shutil
import pandas as pd
from flask import render_template, jsonify, request

BASE = os.path.dirname(os.path.abspath(__file__))
REQUIRED = ["Order ID", "Date", "Product", "Category", "Price", "Quantity", "Total Sales",
            "Customer Name", "Customer Location", "Payment Method", "Status"]
DIMS = {"Category": "Category", "Product": "Product", "Location": "Customer Location",
        "Payment Method": "Payment Method", "Status": "Status", "Month": "Month",
        "Weekday": "Weekday", "Amount Band": "Amount_Band", "Customer": "Customer Name"}
MEASURES = {"count": "Orders", "revenue": "Revenue ($)", "avg": "Avg order value ($)", "units": "Units", "cancelled": "Cancelled orders"}
_df = None


def data_file():
    p = os.environ.get("DATA_FILE")
    if p and os.path.exists(p): return p
    for pat in ("amazon_sales*.xlsx", "amazon_sales*.csv", "sales_data*.xlsx", "sales_data*.csv"):
        f = sorted(glob.glob(os.path.join(BASE, pat)))
        if f: return f[0]
    raise FileNotFoundError("Dataset not found. Put amazon_sales_data...xlsx in the project folder.")


def prepare(raw):
    raw = raw.copy()
    raw.columns = [str(c).strip() for c in raw.columns]
    if "Order ID" not in raw.columns:
        raw = raw.rename(columns={raw.columns[0]: "Order ID"})
    miss = [c for c in REQUIRED if c not in raw.columns]
    if miss: raise ValueError("Missing columns: " + ", ".join(miss))
    raw["Date"] = pd.to_datetime(raw["Date"], errors="coerce")
    if raw["Date"].isna().any(): raise ValueError("Some dates could not be read.")
    raw["Month"] = raw["Date"].dt.month_name()
    raw["Weekday"] = raw["Date"].dt.day_name()
    raw["Amount_Band"] = pd.cut(raw["Total Sales"], [-1, 100, 500, 1500, float("inf")],
                                labels=["Under $100", "$100-500", "$500-1500", "Over $1500"]).astype(str)
    raw["Is_Cancelled"] = (raw["Status"] == "Cancelled").astype(int)
    return raw


def read_any(path):
    return pd.read_csv(path) if path.lower().endswith(".csv") else pd.read_excel(path)


def get_df():
    global _df
    if _df is None: _df = prepare(read_any(data_file()))
    return _df


def reload_df():
    global _df
    _df = None
    return get_df()


def filt(df, status):
    return df if status in (None, "", "All") else df[df["Status"] == status]


def agg(df, by, m):
    g = df.groupby(by)
    return {"count": g.size, "revenue": lambda: g["Total Sales"].sum(), "avg": lambda: g["Total Sales"].mean(),
            "units": lambda: g["Quantity"].sum(), "cancelled": lambda: g["Is_Cancelled"].sum()}[m]()


def kpis(df):
    d = df[df["Status"] == "Completed"]
    return dict(revenue=round(float(d["Total Sales"].sum())), orders=int(len(d)), total_orders=int(len(df)),
                aov=round(float(d["Total Sales"].mean()), 2), cancel_rate=round(float(df["Is_Cancelled"].mean() * 100), 1),
                units=int(d["Quantity"].sum()))


def series(s, n=None):
    s = s.sort_values(ascending=False)
    if n: s = s.head(n)
    return dict(labels=[str(i) for i in s.index], values=[round(float(v), 2) for v in s.values])


def register(app):
    L = app.login_required

    @app.route("/dataset")
    @L
    def dataset_page(): return render_template("dataset.html", active="dataset")

    @app.route("/schema")
    @L
    def schema_page(): return render_template("schema.html", active="schema")

    @app.route("/cube")
    @L
    def cube_page(): return render_template("cube.html", active="cube")

    @app.route("/analytics")
    @L
    def analytics_page(): return render_template("analytics.html", active="analytics")

    @app.get("/api/meta")
    @L
    def meta(): return jsonify(dims=list(DIMS), measures=MEASURES)

    @app.get("/api/dataset")
    @L
    def dataset_info():
        try: df = get_df()
        except Exception as e: return jsonify(ok=False, msg=str(e)), 500
        cols = [("Order ID", "Unique order number"), ("Date", "Date of the order"), ("Product", "Item sold"),
                ("Category", "Product group"), ("Price", "Unit price in dollars"), ("Quantity", "Units in the order"),
                ("Total Sales", "Price x Quantity"), ("Customer Name", "Buyer"), ("Customer Location", "Buyer city"),
                ("Payment Method", "How they paid"), ("Status", "Completed, Pending or Cancelled")]
        return jsonify(ok=True, rows=len(df), cols=11, file=os.path.basename(data_file()),
                       cancelled=int(df["Is_Cancelled"].sum()), cancel_rate=round(df["Is_Cancelled"].mean() * 100, 1),
                       date_min=str(df["Date"].min().date()), date_max=str(df["Date"].max().date()),
                       missing=int(df[REQUIRED].isna().sum().sum()), columns=cols,
                       dims={"dim_date": df["Date"].nunique(), "dim_product": df["Product"].nunique(),
                             "dim_customer": len(df[["Customer Name", "Customer Location"]].drop_duplicates()),
                             "dim_payment": df["Payment Method"].nunique(), "dim_status": df["Status"].nunique(), "fact_sales": len(df)})

    @app.get("/api/preview")
    @L
    def preview():
        df, page = get_df(), max(0, request.args.get("page", 0, int))
        part = df[REQUIRED].iloc[page * 15:(page + 1) * 15].copy()
        part["Date"] = part["Date"].dt.strftime("%Y-%m-%d")
        return jsonify(cols=REQUIRED, rows=part.values.tolist(), pages=(len(df) + 14) // 15)

    @app.get("/api/cube")
    @L
    def cube():
        a = request.args
        ax = [a.get("x", "Category"), a.get("y", "Payment Method"), a.get("z", "Month")]
        m, status = a.get("measure", "count"), a.get("status", "All")
        if any(i not in DIMS for i in ax) or m not in MEASURES: return jsonify(ok=False, msg="Unknown dimension or measure."), 400
        if len(set(ax)) < 3: return jsonify(ok=False, msg="Choose three different dimensions."), 400
        df, cols = filt(get_df(), status), [DIMS[i] for i in ax]
        keep = [list(df[c].value_counts().head(8).index) for c in cols]
        for c, k in zip(cols, keep): df = df[df[c].isin(k)]
        r = agg(df, cols, m)
        cells = [dict(x=str(i[0]), y=str(i[1]), z=str(i[2]), v=round(float(v), 2)) for i, v in r.items()]
        return jsonify(ok=True, x=[str(i) for i in keep[0]], y=[str(i) for i in keep[1]], z=[str(i) for i in keep[2]], cells=cells, measure=MEASURES[m])

    @app.get("/api/analytics")
    @L
    def analytics():
        df = get_df()
        d = df[df["Status"] == "Completed"]
        w = d.set_index("Date")["Total Sales"].resample("W-SUN").sum()
        w = w.iloc[1:-1] if len(w) > 4 else w
        weekly = dict(labels=[x.strftime("%d %b") for x in w.index], values=[round(float(v)) for v in w.values])
        rate = (df.groupby("Category")["Is_Cancelled"].mean() * 100).round(1)
        return jsonify(kpis=kpis(df), charts=dict(
            weekly=weekly, category=series(d.groupby("Category")["Total Sales"].sum()),
            location=series(d.groupby("Customer Location")["Total Sales"].sum()),
            payment=series(d.groupby("Payment Method").size()),
            cancel=series(rate), band=series(d.groupby("Amount_Band")["Total Sales"].sum()),
            product=series(d.groupby("Product")["Total Sales"].sum(), 10)))

    @app.get("/api/build")
    @L
    def build():
        a = request.args
        dim, m, top = a.get("dim", "Category"), a.get("measure", "revenue"), min(30, max(1, a.get("top", 10, int)))
        if dim not in DIMS or m not in MEASURES: return jsonify(ok=False, msg="Unknown dimension or measure."), 400
        df = filt(get_df(), a.get("status", "Completed"))
        if df.empty: return jsonify(ok=False, msg="No data for that filter."), 400
        s = agg(df, DIMS[dim], m)
        return jsonify(ok=True, title=f"{MEASURES[m]} by {dim}", **series(s, top))
