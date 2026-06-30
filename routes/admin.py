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
        
    # Fetch existing API keys
    rows = db_service.query("SELECT key_name, key_value FROM system_settings")
    settings = {row["key_name"]: row["key_value"] for row in rows} if rows else {}
    
    # Fetch Users
    users = db_service.query("SELECT p.*, COALESCE(u.subscription_tier, 'free') as subscription_tier FROM profiles p LEFT JOIN user_usage u ON p.id = u.user_id ORDER BY p.created_at DESC")
    
    # Fetch Payment Proofs (Pending first)
    proofs = db_service.query("SELECT pp.*, p.email, p.full_name FROM payment_proofs pp JOIN profiles p ON pp.user_id = p.id ORDER BY CASE WHEN pp.status = 'pending' THEN 0 ELSE 1 END, pp.created_at DESC")
    
    # Fetch Genuine Support Requests
    requests_list = db_service.query("SELECT sr.*, p.email, p.full_name FROM support_requests sr JOIN profiles p ON sr.user_id = p.id WHERE sr.is_genuine = 1 ORDER BY CASE WHEN sr.status = 'open' THEN 0 ELSE 1 END, sr.created_at DESC")
    
    return render_template("admin/dashboard.html", settings=settings, users=users, proofs=proofs, requests=requests_list)

@admin_bp.route("/proof/<proof_id>/<action>", methods=["POST"])
def handle_proof(proof_id, action):
    if not session.get("is_superadmin"):
        return redirect(url_for("admin.login"))
        
    proof = db_service.query("SELECT * FROM payment_proofs WHERE id = ?", (proof_id,), one=True)
    if not proof:
        flash("Proof not found", "error")
        return redirect(url_for("admin.dashboard"))
        
    if action == "approve":
        db_service.execute("UPDATE payment_proofs SET status = 'approved' WHERE id = ?", (proof_id,))
        db_service.execute("INSERT INTO user_usage (user_id, subscription_tier) VALUES (?, 'premium') ON CONFLICT(user_id) DO UPDATE SET subscription_tier = 'premium'", (proof["user_id"],))
        flash("Proof approved and user upgraded to premium.", "success")
    elif action == "reject":
        db_service.execute("UPDATE payment_proofs SET status = 'rejected' WHERE id = ?", (proof_id,))
        flash("Proof rejected.", "success")
        
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/request/<request_id>/close", methods=["POST"])
def close_request(request_id):
    if not session.get("is_superadmin"):
        return redirect(url_for("admin.login"))
        
    db_service.execute("UPDATE support_requests SET status = 'closed' WHERE id = ?", (request_id,))
    flash("Request marked as closed.", "success")
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/request/<request_id>/reply", methods=["POST"])
def reply_request(request_id):
    if not session.get("is_superadmin"):
        return redirect(url_for("admin.login"))
        
    reply_message = request.form.get("reply_message")
    if not reply_message:
        flash("Reply message cannot be empty.", "error")
        return redirect(url_for("admin.dashboard"))
        
    # Get request and user info
    req = db_service.query(
        "SELECT sr.*, p.email, p.full_name FROM support_requests sr JOIN profiles p ON sr.user_id = p.id WHERE sr.id = ?",
        (request_id,), one=True
    )
    
    if req and req["email"]:
        from services.email_service import email_service
        success = email_service.send_support_reply(req["email"], req["full_name"] or "User", reply_message)
        
        if success:
            db_service.execute("UPDATE support_requests SET status = 'closed' WHERE id = ?", (request_id,))
            flash(f"Reply sent to {req['email']} and request closed.", "success")
        else:
            flash("Failed to send email. Check Resend configuration.", "error")
    else:
        flash("Request or user email not found.", "error")
        
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/user/<user_id>/reset_password", methods=["POST"])
def reset_password(user_id):
    if not session.get("is_superadmin"):
        return redirect(url_for("admin.login"))
        
    user = db_service.query("SELECT * FROM profiles WHERE id = ?", (user_id,), one=True)
    if user and user["email"]:
        from services.email_service import email_service
        from routes.auth import _generate_otp
        
        otp, otp_hash = _generate_otp()
        from datetime import datetime, timedelta
        expires_at = (datetime.now() + timedelta(minutes=15)).isoformat()
        
        import uuid
        db_service.execute("INSERT INTO password_reset_otps (id, email, otp_hash, expires_at) VALUES (?, ?, ?, ?)",
                           (str(uuid.uuid4()), user["email"], otp_hash, expires_at))
        
        email_service.send_password_reset(user["email"], otp)
        flash(f"Password reset email sent to {user['email']}.", "success")
    else:
        flash("User or email not found.", "error")
        
    return redirect(url_for("admin.dashboard"))
