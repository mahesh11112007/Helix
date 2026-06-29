from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from services.db_service import db_service

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if username == "Mahesh" and password == "Mahesh@1111":
            session["is_superadmin"] = True
            flash("Admin logged in successfully", "success")
            return redirect(url_for("admin.dashboard"))
        else:
            flash("Invalid credentials", "error")
            return redirect(url_for("admin.login"))
            
    return render_template("admin/login.html")

@admin_bp.route("/logout")
def logout():
    session.pop("is_superadmin", None)
    flash("Admin logged out", "success")
    return redirect(url_for("dashboard.index"))

@admin_bp.route("/", methods=["GET", "POST"])
def dashboard():
    if not session.get("is_superadmin"):
        return redirect(url_for("admin.login"))
        
    if request.method == "POST":
        keys_to_save = {
            "GEMINI_API_KEYS": request.form.get("gemini_keys", "").strip(),
            "NVIDIA_NIM_API_KEYS": request.form.get("nvidia_keys", "").strip(),
            "GROQ_API_KEYS": request.form.get("groq_keys", "").strip(),
            "OPENROUTER_API_KEYS": request.form.get("openrouter_keys", "").strip()
        }
        
        for k, v in keys_to_save.items():
            # Upsert
            existing = db_service.query("SELECT * FROM system_settings WHERE key_name = ?", (k,), one=True)
            if existing:
                db_service.execute("UPDATE system_settings SET key_value = ?, updated_at = CURRENT_TIMESTAMP WHERE key_name = ?", (v, k))
            else:
                db_service.execute("INSERT INTO system_settings (key_name, key_value) VALUES (?, ?)", (k, v))
                
        flash("Global API Keys updated successfully!", "success")
        return redirect(url_for("admin.dashboard"))
        
    # Fetch existing
    rows = db_service.query("SELECT key_name, key_value FROM system_settings")
    settings = {row["key_name"]: row["key_value"] for row in rows} if rows else {}
    
    return render_template("admin/dashboard.html", settings=settings)
