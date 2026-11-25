"""Admin: manage users and dataset."""
import os, shutil, tempfile
from flask import render_template, jsonify, request
import phase2


def register(app):
    A = app.admin_required

    @app.route("/admin")
    @A
    def admin_page(): return render_template("admin.html", active="admin")

    @app.get("/api/admin/users")
    @A
    def users():
        from app import db
        with db() as c: rows = c.execute("SELECT name,email,created FROM users ORDER BY created DESC").fetchall()
        return jsonify(users=[dict(r) for r in rows])  # never returns passwords or OTPs

    @app.post("/api/admin/delete")
    @A
    def delete_user():
        from app import db
        email = ((request.get_json(silent=True) or {}).get("email") or "").lower()
        with db() as c:
            n = c.execute("DELETE FROM users WHERE email=?", (email,)).rowcount
            c.execute("DELETE FROM otps WHERE ident=?", (email,))
        return jsonify(ok=bool(n), msg="User deleted." if n else "User not found.")

    @app.post("/api/admin/upload")
    @A
    def upload():
        f = request.files.get("file")
        if not f or not f.filename.lower().endswith((".xlsx", ".csv")):
            return jsonify(ok=False, msg="Choose an .xlsx or .csv file."), 400
        tmp = os.path.join(tempfile.gettempdir(), "upload_" + os.path.basename(f.filename))
        f.save(tmp)
        try: phase2.prepare(phase2.read_any(tmp))
        except Exception as e:
            os.remove(tmp)
            return jsonify(ok=False, msg=f"Validation failed: {e}"), 400
        cur = phase2.data_file()
        shutil.copy(cur, cur + ".bak")
        dest = os.path.join(phase2.BASE, "amazon_sales_data_uploaded" + os.path.splitext(tmp)[1].lower())
        shutil.copy(tmp, dest); os.remove(tmp)
        if os.path.abspath(cur) != os.path.abspath(dest): os.replace(cur, cur + ".old")
        phase2._df = None
        return jsonify(ok=True, msg=f"Dataset replaced ({len(phase2.reload_df())} rows). Old file kept as a backup.")

    @app.post("/api/admin/reload")
    @A
    def reload():
        try: return jsonify(ok=True, msg=f"Reloaded {len(phase2.reload_df())} rows.")
        except Exception as e: return jsonify(ok=False, msg=str(e)), 500
