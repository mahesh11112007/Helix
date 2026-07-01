import uuid
import json
from datetime import datetime, timedelta
from services.db_service import db_service

class WeeklyTestService:
    def check_and_generate(self, user_id):
        """
        Check if the user needs a weekly test generated for their active semester.
        Tests are generated on Sundays.
        """
        today = datetime.now()
        
        # Determine the cutoff date (7 days ago)
        seven_days_ago = today - timedelta(days=7)
        cutoff_date = seven_days_ago.replace(hour=0, minute=0, second=0, microsecond=0)
        
        print(f"[DEBUG] check_and_generate for user_id: {user_id}")
        semesters = db_service.query("SELECT * FROM semesters WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        if not semesters:
            print(f"[DEBUG] No semesters found for user {user_id}")
            return
            
        print(f"[DEBUG] Found {len(semesters)} semesters for user {user_id}")
        active_sem = semesters[0]
        
        # Check if a combined test already exists in the last 7 days
        existing_test = db_service.query(
            "SELECT id FROM weekly_tests WHERE user_id = ? AND subject_id = 'ALL' AND created_at >= ?",
            (user_id, cutoff_date.isoformat())
        )
        
        if not existing_test:
            # Delete old tests to only keep the latest one (cleanup)
            db_service.execute("DELETE FROM weekly_test_answers WHERE test_id IN (SELECT id FROM weekly_tests WHERE user_id = ?)", (user_id,))
            db_service.execute("DELETE FROM weekly_tests WHERE user_id = ?", (user_id,))
            
            # Generate a new test instantly from question bank
            self.generate_instant_test(user_id, active_sem["id"])
                
    def generate_instant_test(self, user_id, sem_id):
        try:
            # 1. Fetch all subjects for this semester
            subjects = db_service.query("SELECT id, name FROM subjects WHERE semester_id = ?", (sem_id,))
            subject_ids = [sub["id"] for sub in subjects]
            
            if not subject_ids:
                return

            # Format subject_ids for SQL IN clause safely
            placeholders = ','.join(['?'] * len(subject_ids))
            
            # 2. Fetch 20 random unseen questions from the bank for these subjects
            query = f"""
                SELECT * FROM question_bank 
                WHERE subject_id IN ({placeholders}) 
                AND id NOT IN (SELECT question_id FROM user_attempted_questions WHERE user_id = ?)
                ORDER BY RANDOM() 
                LIMIT 20
            """
            # Params: subject_ids followed by user_id
            params = tuple(subject_ids) + (user_id,)
            questions = db_service.query(query, params)
            
            # If not enough unseen questions, fetch any random questions to fill the gap
            if len(questions) < 20:
                needed = 20 - len(questions)
                fallback_query = f"""
                    SELECT * FROM question_bank 
                    WHERE subject_id IN ({placeholders}) 
                    ORDER BY RANDOM() 
                    LIMIT ?
                """
                fallback_params = tuple(subject_ids) + (needed,)
                fallback_questions = db_service.query(fallback_query, fallback_params)
                
                # Combine them, ensuring no exact duplicates in the current list if possible
                existing_ids = {q["id"] for q in questions}
                for fq in fallback_questions:
                    if fq["id"] not in existing_ids:
                        questions.append(fq)
                        existing_ids.add(fq["id"])

            if not questions:
                # No questions exist in bank at all yet
                print("No questions found in question bank for these subjects.")
                return

            # 3. Save test
            test_id = str(uuid.uuid4())
            # Convert questions to JSON array
            test_data = []
            for q in questions:
                # Mark as attempted
                db_service.execute(
                    "INSERT OR IGNORE INTO user_attempted_questions (user_id, question_id) VALUES (?, ?)", 
                    (user_id, q["id"])
                )
                
                test_data.append({
                    "id": q["id"],
                    "question": q["question"],
                    "options": json.loads(q["options"]),
                    "correct_answer": q["correct_answer"],
                    "explanation": q["explanation"],
                    "difficulty": q["difficulty"]
                })
                
            db_service.execute(
                """INSERT INTO weekly_tests (id, user_id, subject_id, title, test_data, status, total_questions)
                   VALUES (?, ?, 'ALL', ?, ?, 'pending', ?)""",
                (test_id, user_id, "Weekly Assessment: Advanced Review", json.dumps(test_data), len(test_data))
            )
            
        except Exception as e:
            print(f"Error generating weekly test from bank: {e}")

weekly_test_service = WeeklyTestService()
