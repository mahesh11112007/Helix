from flask import Blueprint, render_template, request, flash, redirect, url_for, session
import os
import json
import fitz  # PyMuPDF
from services.syllabus_service import syllabus_service
from services.ai_service import ai_service
from services.db_service import db_service

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

def get_current_user():
    if "user_id" not in session:
        return None
    return {"id": session["user_id"]}

def is_admin(user):
    # For now, just allow any logged in user as admin, or check a specific flag
    # Assuming any authenticated user can access for this MVP.
    return user is not None

@admin_bp.route("/")
def index():
    user = get_current_user()
    if not is_admin(user):
        flash("Unauthorized", "error")
        return redirect(url_for("auth.login"))
    
    # We allow manual typing of education, board, year, group to create new folders/files if they don't exist
    return render_template("admin/upload.html")

@admin_bp.route("/upload-syllabus", methods=["POST"])
def upload_syllabus():
    user = get_current_user()
    if not is_admin(user):
        return redirect(url_for("auth.login"))

    education = request.form.get("education", "").strip().lower().replace(" ", "_")
    board = request.form.get("board", "").strip().lower().replace(" ", "_")
    year = request.form.get("year", "").strip().lower().replace(" ", "_")
    group = request.form.get("group", "").strip().upper()
    
    pdf_file = request.files.get("pdf_file")

    if not all([education, board, year, group, pdf_file]):
        flash("Please provide all fields and a PDF file.", "error")
        return redirect(url_for("admin.index"))

    try:
        # Extract text from PDF
        pdf_bytes = pdf_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
            
        if not text.strip():
            flash("Could not extract text from the PDF. It might be an image-only PDF.", "error")
            return redirect(url_for("admin.index"))

        # Send to AI for parsing
        extracted_subjects = ai_service.parse_syllabus(text)
        
        if not extracted_subjects or "subjects" not in extracted_subjects:
            flash("AI failed to extract syllabus accurately. Please try a cleaner PDF.", "error")
            return redirect(url_for("admin.index"))

        # Define file path
        target_dir = os.path.join(syllabus_service.data_dir, education, board)
        os.makedirs(target_dir, exist_ok=True)
        file_path = os.path.join(target_dir, f"{year}.json")

        # Load existing or create new JSON structure
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {
                "year": request.form.get("year"), # original case
                "groups": {}
            }

        if "groups" not in data:
            data["groups"] = {}

        # Save to the specific group
        data["groups"][group] = extracted_subjects["subjects"]

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        flash(f"Successfully added syllabus for {group} in {education}/{board}/{year}!", "success")
        return redirect(url_for("admin.index"))

    except Exception as e:
        print(f"Error processing PDF: {e}")
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for("admin.index"))
