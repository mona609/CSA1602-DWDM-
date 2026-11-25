"""Chart-only PDF report by category and month."""
import io, base64
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from flask import render_template, jsonify, request, send_file
import phase2

TEAL, NAVY, RED, GREEN = "#2dd4bf", "#0b1b34", "#ef4444", "#22c55e"
PAL = ["#2dd4bf", "#38bdf8", "#818cf8", "#f59e0b", "#f472b6", "#a3e635", "#fb923c", "#94a3b8"]


def subset(cat, month):
    df = phase2.get_df()
    full = df
    if cat and cat != "All": df = df[df["Category"] == cat]
    if month and month != "All": df = df[df["Month"] == month]
    return full, df


def tile(ax, label, value, color=TEAL):
    ax.axis("off"); ax.set_facecolor(NAVY)
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, color="#eef6f6", ec=color, lw=2))
    ax.text(.5, .62, value, ha="center", va="center", fontsize=20, weight="bold", color=NAVY, transform=ax.transAxes)
    ax.text(.5, .22, label, ha="center", va="center", fontsize=10, color="#475569", transform=ax.transAxes)


def bar(ax, s, title, horiz=True, color=TEAL):
    s = s.sort_values()
    (ax.barh if horiz else ax.bar)(s.index.astype(str), s.values, color=color)
    ax.set_title(title, fontsize=11, weight="bold")
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)


def donut(ax, s, title):
    ax.pie(s.values, labels=s.index, colors=PAL, wedgeprops=dict(width=.4), autopct="%1.0f%%", textprops=dict(fontsize=8), pctdistance=.8)
    ax.set_title(title, fontsize=11, weight="bold")


def make_pages(cat, month):
    full, df = subset(cat, month)
    if df.empty: raise ValueError("No orders for that selection.")
    done, canc = df[df["Status"] == "Completed"], df[df["Status"] == "Cancelled"]
    rev, allrev = done["Total Sales"].sum(), full[full["Status"] == "Completed"]["Total Sales"].sum()
    cr, cr_all = df["Is_Cancelled"].mean() * 100, full["Is_Cancelled"].mean() * 100
    label = f"{cat or 'All'} | {month or 'All'}"
    pages = []

    f = plt.figure(figsize=(11, 8.5)); f.suptitle(f"RetailIQ: Sales Overview ({label})", fontsize=14, weight="bold")
    g = f.add_gridspec(3, 4, height_ratios=[.55, 1.2, 1.2], hspace=.55, wspace=.45)
    tile(f.add_subplot(g[0, 0]), "Revenue (completed)", f"${rev:,.0f}")
    tile(f.add_subplot(g[0, 1]), "Completed orders", f"{len(done)}")
    tile(f.add_subplot(g[0, 2]), "Share of all revenue", f"{rev / allrev * 100:.0f}%")
    same = abs(cr - cr_all) < 0.05
    tile(f.add_subplot(g[0, 3]), "Cancel rate " + ("(same as overall)" if same else "(above overall)" if cr > cr_all else "(below overall)"),
         f"{cr:.0f}% " + ("" if same else "▲" if cr > cr_all else "▼"), TEAL if same else RED if cr > cr_all else GREEN)
    ax = f.add_subplot(g[1, :2]); w = done.set_index("Date")["Total Sales"].resample("W-SUN").sum()
    ax.plot(w.index, w.values, marker="o", color=TEAL); ax.set_title("Weekly revenue", fontsize=11, weight="bold"); ax.tick_params(axis="x", rotation=30, labelsize=8)
    donut(f.add_subplot(g[1, 2:]), df["Status"].value_counts(), "Order status")
    bar(f.add_subplot(g[2, :2]), done.groupby("Product")["Total Sales"].sum().tail(8), "Revenue by product")
    bar(f.add_subplot(g[2, 2:]), done.groupby("Category")["Total Sales"].sum(), "Revenue by category")
    pages.append(f)

    f = plt.figure(figsize=(11, 8.5)); f.suptitle(f"Where, when and how customers buy ({label})", fontsize=14, weight="bold")
    g = f.add_gridspec(2, 3, hspace=.4, wspace=.5)
    bar(f.add_subplot(g[0, 0]), done.groupby("Customer Location")["Total Sales"].sum(), "Revenue by city")
    donut(f.add_subplot(g[0, 1]), done.groupby("Payment Method").size(), "Payment methods")
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    bar(f.add_subplot(g[0, 2]), done.groupby("Weekday")["Total Sales"].sum().reindex(days).fillna(0), "Revenue by weekday", False)
    f.axes[-1].tick_params(axis="x", rotation=45, labelsize=7)
    bar(f.add_subplot(g[1, 0]), done.groupby("Amount_Band")["Total Sales"].sum(), "Revenue by order size")
    bar(f.add_subplot(g[1, 1]), done.groupby("Customer Name")["Total Sales"].sum().tail(8), "Top customers")
    bar(f.add_subplot(g[1, 2]), (full.groupby("Category")["Is_Cancelled"].mean() * 100), "Cancel rate % (all categories)", color=RED)
    pages.append(f)

    f = plt.figure(figsize=(11, 8.5)); f.suptitle(f"Losses from cancelled orders ({label})", fontsize=14, weight="bold")
    g = f.add_gridspec(3, 3, height_ratios=[.55, 1.2, 1.2], hspace=.55, wspace=.5)
    cv = canc["Total Sales"]
    tile(f.add_subplot(g[0, 0]), "Cancelled value", f"${cv.sum():,.0f}", RED)
    tile(f.add_subplot(g[0, 1]), "Average cancelled order", f"${cv.mean() if len(cv) else 0:,.0f}", RED)
    tile(f.add_subplot(g[0, 2]), "Largest cancelled order", f"${cv.max() if len(cv) else 0:,.0f}", RED)
    for pos, col, t in [((1, 0), "Category", "Lost by category"), ((1, 1), "Customer Location", "Lost by city"), ((1, 2), "Payment Method", "Lost by payment method")]:
        if len(canc): bar(f.add_subplot(g[pos]), canc.groupby(col)["Total Sales"].sum(), t, color=RED)
    if len(canc):
        bar(f.add_subplot(g[2, :2]), canc.groupby("Product")["Total Sales"].sum(), "Lost by product", color=RED)
        ax = f.add_subplot(g[2, 2]); m = canc.groupby("Month")["Total Sales"].sum(); ax.bar(m.index, m.values, color=RED); ax.set_title("Lost by month", fontsize=11, weight="bold")
    pages.append(f)
    return pages


def register(app):
    L = app.login_required

    @app.route("/report")
    @L
    def report_page():
        df = phase2.get_df()
        return render_template("report.html", active="report", cats=sorted(df["Category"].unique()), months=[m for m in ["February", "March", "April"] if m in set(df["Month"])])

    @app.get("/api/report/preview")
    @L
    def report_preview():
        try: pages = make_pages(request.args.get("category", "All"), request.args.get("month", "All"))
        except ValueError as e: return jsonify(ok=False, msg=str(e)), 400
        out = []
        for p in pages:
            b = io.BytesIO(); p.savefig(b, format="png", dpi=70); plt.close(p)
            out.append("data:image/png;base64," + base64.b64encode(b.getvalue()).decode())
        return jsonify(ok=True, images=out)

    @app.get("/report/pdf")
    @L
    def pdf():
        cat, month = request.args.get("category", "All"), request.args.get("month", "All")
        try: pages = make_pages(cat, month)
        except ValueError as e: return jsonify(ok=False, msg=str(e)), 400
        b = io.BytesIO()
        with PdfPages(b) as pp:
            for p in pages: pp.savefig(p); plt.close(p)
        b.seek(0)
        return send_file(b, mimetype="application/pdf", as_attachment=True, download_name=f"RetailIQ_Report_{cat}_{month}.pdf".replace(" ", "_"))
