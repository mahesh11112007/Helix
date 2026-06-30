
from flask import Blueprint, request, jsonify, redirect, url_for, render_template, current_app, flash
from services.billing_service import billing_service
from routes.dashboard import get_current_user

billing_bp = Blueprint("billing", __name__)

@billing_bp.route("/upgrade", methods=["GET"])
def upgrade_page():
    from services.db_service import db_service
    user = get_current_user()
    if not user:
        return redirect(url_for("auth.login"))
        
    profile = db_service.query("SELECT premium_request_status, is_premium FROM profiles WHERE id = ?", (user["id"],), one=True)
    if profile:
        profile = dict(profile)
        user["premium_request_status"] = profile.get("premium_request_status")
        user["is_premium"] = profile.get("is_premium")
        
    return render_template("dashboard/upgrade.html", user=user)

@billing_bp.route("/checkout", methods=["POST"])
def checkout():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    phone = request.form.get("phone")
    if not phone or len(phone) != 10:
        flash("Please enter a valid 10-digit mobile number.", "error")
        return redirect(url_for("billing.upgrade_page"))

    # Test Mode Simulation
    if not billing_service.api_key or billing_service.api_key == "test_placeholder_api_key":
        # Simulate payment success instantly
        billing_service.upgrade_user_to_premium(user["id"])
        flash("Instamojo Test Mode: Automatically upgraded to Premium!", "success")
        return redirect(url_for("billing.success"))
        
    success_url = request.host_url.rstrip("/") + url_for("billing.success")
    cancel_url = request.host_url.rstrip("/") + url_for("billing.upgrade_page")
    
    checkout_url = billing_service.create_checkout_session(user["id"], user["email"], phone, success_url, cancel_url)
    
    if checkout_url:
        return redirect(checkout_url)
    else:
        flash("Unable to connect to Payment Gateway right now. Please try again later.", "error")
        return redirect(url_for("billing.upgrade_page"))

@billing_bp.route("/upgrade/success", methods=["GET"])
def success():
    user = get_current_user()
    if not user:
        return redirect(url_for("auth.login"))
        
    # Instamojo redirects here with query params: payment_id, payment_status, payment_request_id
    payment_id = request.args.get("payment_id")
    payment_status = request.args.get("payment_status")
    payment_request_id = request.args.get("payment_request_id")
    
    # If returned from live Instamojo payment, verify it server-side before upgrading
    if payment_id and payment_request_id and payment_status == "Credit":
        is_valid = billing_service.verify_payment(payment_request_id, payment_id)
        if is_valid:
            billing_service.upgrade_user_to_premium(user["id"])
        else:
            flash("Payment verification failed. If money was deducted, please contact support.", "error")
            return redirect(url_for("billing.upgrade_page"))
            
    return render_template("dashboard/upgrade.html", user=user, success=True)

@billing_bp.route("/proof", methods=["POST"])
def upload_proof():
    user = get_current_user()
    if not user:
        return redirect(url_for("auth.login"))
        
    if "proof_image" not in request.files:
        flash("No image uploaded.", "error")
        return redirect(url_for("billing.upgrade_page"))
        
    file = request.files["proof_image"]
    if file.filename == "":
        flash("No selected file.", "error")
        return redirect(url_for("billing.upgrade_page"))
        
    if file:
        import uuid
        import os
        from werkzeug.utils import secure_filename
        
        # Save file to static/uploads/proofs directory
        upload_dir = os.path.join(current_app.root_path, "../static/uploads/proofs")
        os.makedirs(upload_dir, exist_ok=True)
        
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
        new_filename = f"{uuid.uuid4()}.{ext}"
        filepath = os.path.join(upload_dir, new_filename)
        
        file.save(filepath)
        
        # Insert into DB
        from services.db_service import db_service
        proof_id = str(uuid.uuid4())
        db_path = f"static/uploads/proofs/{new_filename}"
        
        db_service.execute(
            "INSERT INTO payment_proofs (id, user_id, file_path, status) VALUES (?, ?, ?, 'pending')",
            (proof_id, user["id"], db_path)
        )
        
        flash("Payment proof uploaded successfully! Our team will verify it shortly.", "success")
        return redirect(url_for("billing.upgrade_page"))

@billing_bp.route("/request-premium", methods=["POST"])
def request_premium():
    from services.db_service import db_service
    user = get_current_user()
    if not user:
        return redirect(url_for("auth.login"))
        
    try:
        db_service.execute("UPDATE profiles SET premium_request_status = 'pending' WHERE id = ?", (user["id"],))
        flash("Your request for Premium has been submitted to the Admin!", "success")
    except Exception as e:
        print(f"Error requesting premium: {e}")
        flash("Could not submit request at this time.", "error")
        
    return redirect(url_for("billing.upgrade_page"))
