import uuid
import json
from datetime import datetime, timedelta
from services.db_service import db_service
from services.ai_service import ai_service

class WeeklyTestService:
    def check_and_generate(self, user_id):
        """
        Check if the user needs weekly tests generated for their active subjects.
        Tests are generated on Sundays.
        """
        today = datetime.now()
        
        # Determine the most recent Sunday (or today if it is Sunday)
        # weekday() returns 0 for Monday, 6 for Sunday
        days_since_sunday = (today.weekday() - 6) % 7
        last_sunday = today - timedelta(days=days_since_sunday)
        last_sunday_start = last_sunday.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get user's active semester
        print(f"[DEBUG] check_and_generate for user_id: {user_id}")
        semesters = db_service.query("SELECT * FROM semesters WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        if not semesters:
            print(f"[DEBUG] No semesters found for user {user_id}")
            return
            
        print(f"[DEBUG] Found {len(semesters)} semesters for user {user_id}")
        active_sem = semesters[0]
        subjects = db_service.query("SELECT * FROM subjects WHERE semester_id = ?", (active_sem["id"],))
        
        for subject in subjects:
            # Check if a test already exists for this subject since last Sunday
            existing_test = db_service.query(
                "SELECT id FROM weekly_tests WHERE user_id = ? AND subject_id = ? AND created_at >= ?",
                (user_id, subject["id"], last_sunday_start.isoformat())
            )
            
            if not existing_test:
                # Generate a new test in the background
                self.queue_test_generation(user_id, subject["id"], subject["name"], last_sunday_start)
                
    def queue_test_generation(self, user_id, subject_id, subject_name, week_start_date):
        """
        Creates a background task to generate the test so the user doesn't wait on login.
        """
        task_id = str(uuid.uuid4())
        db_service.execute(
            """INSERT INTO background_tasks (id, user_id, task_type, status, message)
               VALUES (?, ?, ?, ?, ?)""",
            (task_id, user_id, f"generate_weekly_test_{subject_id}", "pending", f"Generating Weekly Test for {subject_name}")
        )
        
        import threading
        thread = threading.Thread(target=self._generate_test_task, args=(user_id, subject_id, subject_name, task_id))
        thread.daemon = True
        thread.start()
        
    def _generate_test_task(self, user_id, subject_id, subject_name, task_id):
        try:
            db_service.execute("UPDATE background_tasks SET status = 'in_progress' WHERE id = ?", (task_id,))
            
            # 1. Fetch topics for this subject
            units = db_service.query("SELECT id, name FROM units WHERE subject_id = ?", (subject_id,))
            topics_list = []
            for unit in units:
                topics = db_service.query("SELECT name FROM topics WHERE unit_id = ?", (unit["id"],))
                topics_list.extend([t["name"] for t in topics])
                
            topic_str = ", ".join(topics_list[:15]) # Limit context to avoid huge prompts
            
            # 2. Call AI to generate Short Answer questions
            prompt = f"""
            You are a strict academic examiner. Create a comprehensive Weekly Assessment (Short Answer format) 
            for the subject "{subject_name}". 
            
            Here are some topics covered recently: {topic_str}.
            
            Generate exactly 10 Short Answer questions. 
            For each question, provide the "question" and the "expected_answer" (the grading rubric/key points).
            
            Output MUST be strict JSON in this format:
            {{
                "title": "Weekly Assessment: {subject_name}",
                "questions": [
                    {{
                        "question": "What is...",
                        "expected_answer": "Key point 1, Key point 2..."
                    }}
                ]
            }}
            """
            
            response = ai_service._generate_partial(prompt)
            # Find JSON block
            test_created = False
            if response and isinstance(response, dict) and "questions" in response:
                json_data = response
                
                test_id = str(uuid.uuid4())
                db_service.execute(
                    """INSERT INTO weekly_tests (id, user_id, subject_id, title, test_data, status, total_questions)
                       VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
                    (test_id, user_id, subject_id, json_data.get("title", f"{subject_name} Weekly Test"), json.dumps(json_data.get("questions", [])), len(json_data.get("questions", [])))
                )
                test_created = True
                    
            if not test_created:
                # Fallback mock test due to API rate limits
                test_id = str(uuid.uuid4())
                mock_data = [
                    {
                        "question": f"What is the most important concept you learned in {subject_name} this week?",
                        "expected_answer": "Any core concept from the subject."
                    },
                    {
                        "question": f"Explain a key theorem or formula related to {subject_name}.",
                        "expected_answer": "A relevant theorem or formula and its explanation."
                    }
                ]
                db_service.execute(
                    """INSERT INTO weekly_tests (id, user_id, subject_id, title, test_data, status, total_questions)
                       VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
                    (test_id, user_id, subject_id, f"{subject_name} Mock Weekly Test (AI Rate Limited)", json.dumps(mock_data), 2)
                )
            
            db_service.execute("UPDATE background_tasks SET status = 'completed' WHERE id = ?", (task_id,))
        except Exception as e:
            print(f"Error generating weekly test: {e}")
            db_service.execute("UPDATE background_tasks SET status = 'failed', message = ? WHERE id = ?", (str(e), task_id))

weekly_test_service = WeeklyTestService()
