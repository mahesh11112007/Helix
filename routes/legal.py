from flask import Blueprint, render_template

legal_bp = Blueprint("legal", __name__)

@legal_bp.route("/contact")
def contact():
    return render_template("legal/contact.html")

@legal_bp.route("/terms")
def terms():
    return render_template("legal/terms.html")

@legal_bp.route("/refund-policy")
def refund_policy():
    return render_template("legal/refund.html")

@legal_bp.route("/privacy-policy")
def privacy_policy():
    return render_template("legal/privacy.html")
