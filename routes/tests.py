import os
import uuid
import json
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from services.db_service import db_service
from services.ai_service import ai_service
from routes.dashboard import get_current_user

tests_bp = Blueprint("tests", __name__)

@tests_bp.route("/test/<test_id>", methods=["GET"])
def view_test(test_id):
    user = get_current_user()
    if not user:
        return redirect(url_for("auth.login"))
        
    test = db_service.query("SELECT * FROM weekly_tests WHERE id = ? AND user_id = ?", (test_id, user["id"]), one=True)
    if not test:
        flash("Test not found.", "error")
        return redirect(url_for("dashboard.index"))
        
    subject = db_service.query("SELECT * FROM subjects WHERE id = ?", (test["subject_id"],), one=True)
    
    questions = json.loads(test["test_data"])
    answers = db_service.query("SELECT * FROM weekly_test_answers WHERE test_id = ? ORDER BY question_index ASC", (test_id,))
    
    answered_indices = [a["question_index"] for a in answers]
    
    # If all answered, show results
    if len(answers) >= test["total_questions"] and test["status"] != "completed":
        # Calculate total score
        total_score = sum([a["score"] for a in answers])
        db_service.execute("UPDATE weekly_tests SET status = 'completed', score = ? WHERE id = ?", (total_score, test_id))
        test["status"] = "completed"
        test["score"] = total_score
        
    return render_template("dashboard/take_test.html", test=test, subject=subject, questions=questions, answers=answers, answered_indices=answered_indices)

@tests_bp.route("/test/<test_id>/submit", methods=["POST"])
def submit_answer(test_id):
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
        
    test = db_service.query("SELECT * FROM weekly_tests WHERE id = ? AND user_id = ?", (test_id, user["id"]), one=True)
    if not test:
        return jsonify({"error": "Test not found"}), 404
        
    question_index = int(request.form.get("question_index", -1))
    text_answer = request.form.get("text_answer", "")
    
    questions = json.loads(test["test_data"])
    if question_index < 0 or question_index >= len(questions):
        return jsonify({"error": "Invalid question index"}), 400
        
    question_data = questions[question_index]
    expected_answer = question_data.get("expected_answer", "")
    
    file = request.files.get("image_answer")
    
    image_path = None
    extracted_text = ""
    
    if file and file.filename != "":
        # Handle Image Upload (Handwritten Answer)
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit(".", 1)[1].lower()
        uploads_dir = os.path.join(current_app.root_path, "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        image_path = unique_filename
        full_path = os.path.join(uploads_dir, unique_filename)
        
        file_bytes = file.read()
        with open(full_path, "wb") as f:
            f.write(file_bytes)
            
        # Extract text via Vision AI
        try:
            vision_result = ai_service.process_vision_document(file_bytes)
            extracted_text = vision_result.get("full_text", "")
        except Exception as e:
            print(f"Vision AI Error: {e}")
            extracted_text = "(Error extracting handwriting)"
            
    final_student_answer = text_answer
    if extracted_text:
        final_student_answer = extracted_text if not text_answer else f"{text_answer}\n\n[Handwritten Extraction]: {extracted_text}"
        
    # Grade the answer using AI
    prompt = f"""
    You are grading a Short Answer question.
    Question: {question_data.get("question")}
    Expected Answer/Rubric: {expected_answer}
    
    Student's Answer: {final_student_answer}
    
    Evaluate the student's answer. 
    1. Score it out of 10.
    2. Provide a 1-2 sentence feedback explaining the score.
    
    Return strict JSON:
    {{
        "score": <int 0-10>,
        "feedback": "<string>"
    }}
    """
    
    score = 0
    feedback = "Failed to evaluate."
    
    try:
        response = ai_service._generate_partial(prompt)
        if isinstance(response, dict) and response:
            score = int(response.get("score", 0))
            feedback = response.get("feedback", "Failed to evaluate.")
        else:
            print("Grading Error: Invalid response from AI", response)
    except Exception as e:
        print(f"Grading Error: {e}")
        
    # Save Answer
    ans_id = str(uuid.uuid4())
    db_service.execute(
        """INSERT INTO weekly_test_answers (id, test_id, question_index, user_answer, image_path, score, feedback)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (ans_id, test_id, question_index, final_student_answer, image_path, score, feedback)
    )
    
    flash(f"Answer submitted! You scored {score}/10 on this question.", "success")
    return redirect(url_for("tests.view_test", test_id=test_id))
