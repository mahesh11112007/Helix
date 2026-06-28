
from flask import Blueprint, request, jsonify, redirect, url_for, render_template, current_app, flash
from services.billing_service import billing_service
from routes.dashboard import get_current_user

billing_bp = Blueprint("billing", __name__)

@billing_bp.route("/upgrade", methods=["GET"])
def upgrade_page():
    user = get_current_user()
    if not user:
        return redirect(url_for("auth.login"))
        
    return render_template("dashboard/upgrade.html", user=user)

@billing_bp.route("/checkout", methods=["POST"])
def checkout():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
        
    # Test Mode Simulation
    if not billing_service.api_key or billing_service.api_key == "test_placeholder_api_key":
        # Simulate payment success instantly
        billing_service.upgrade_user_to_premium(user["id"])
        flash("Instamojo Test Mode: Automatically upgraded to Premium!", "success")
        return redirect(url_for("billing.success"))
        
    success_url = request.host_url.rstrip("/") + url_for("billing.success")
    cancel_url = request.host_url.rstrip("/") + url_for("billing.upgrade_page")
    
    checkout_url = billing_service.create_checkout_session(user["id"], user["email"], success_url, cancel_url)
    
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
