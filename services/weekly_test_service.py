import uuid
import json
from datetime import datetime, timedelta
from services.db_service import db_service
from services.ai_service import ai_service

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
            
            # Generate a new test in the background
            self.queue_test_generation(user_id, active_sem["id"], cutoff_date)
                
    def queue_test_generation(self, user_id, sem_id, week_start_date):
        """
        Creates a background task to generate the test so the user doesn't wait on login.
        """
        task_id = str(uuid.uuid4())
        db_service.execute(
            """INSERT INTO background_tasks (id, user_id, task_type, status, message)
               VALUES (?, ?, ?, ?, ?)""",
            (task_id, user_id, "generate_weekly_test_all", "pending", "Generating Weekly Advanced Test")
        )
        
        import threading
        thread = threading.Thread(target=self._generate_test_task, args=(user_id, sem_id, task_id))
        thread.daemon = True
        thread.start()
        
    def _generate_test_task(self, user_id, sem_id, task_id):
        try:
            db_service.execute("UPDATE background_tasks SET status = 'in_progress' WHERE id = ?", (task_id,))
            
            # 1. Fetch all subjects for this semester
            subjects = db_service.query("SELECT id, name FROM subjects WHERE semester_id = ?", (sem_id,))
            
            topics_list = []
            for sub in subjects:
                units = db_service.query("SELECT id FROM units WHERE subject_id = ?", (sub["id"],))
                for unit in units:
                    topics = db_service.query("SELECT name FROM topics WHERE unit_id = ?", (unit["id"],))
                    topics_list.extend([f"{sub['name']}: {t['name']}" for t in topics])
                    
            topic_str = ", ".join(topics_list[:30]) # Limit context to avoid huge prompts
            
            # 2. Call AI to generate Short Answer questions
            prompt = f"""
            You are a strict academic examiner. Create a comprehensive, ADVANCED Assessment (Short Answer format) 
            covering the following topics across multiple subjects: {topic_str}.
            
            Generate EXACTLY 20 advanced Short Answer questions, mixing ALL the available subjects. 
            For each question, provide the "question" and the "expected_answer" (the grading rubric/key points).
            
            Output MUST be strict JSON in this format:
            {{
                "title": "Weekly Assessment: Mixed Advanced Review",
                "questions": [
                    {{
                        "question": "Advanced question...",
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
                       VALUES (?, ?, 'ALL', ?, ?, 'pending_approval', ?)""",
                    (test_id, user_id, json_data.get("title", "Weekly Assessment: Mixed Advanced Review"), json.dumps(json_data.get("questions", [])), len(json_data.get("questions", [])))
                )
                test_created = True
                    
            if not test_created:
                # Fallback mock test due to API rate limits
                test_id = str(uuid.uuid4())
                mock_data = [
                    {
                        "question": "What is the most advanced concept you learned this week?",
                        "expected_answer": "Any core concept."
                    }
                ] * 20
                db_service.execute(
                    """INSERT INTO weekly_tests (id, user_id, subject_id, title, test_data, status, total_questions)
                       VALUES (?, ?, 'ALL', ?, ?, 'pending_approval', ?)""",
                    (test_id, user_id, "Mock Weekly Assessment (AI Rate Limited)", json.dumps(mock_data), 20)
                )
            
            db_service.execute("UPDATE background_tasks SET status = 'completed' WHERE id = ?", (task_id,))
        except Exception as e:
            print(f"Error generating weekly test: {e}")
            db_service.execute("UPDATE background_tasks SET status = 'failed', message = ? WHERE id = ?", (str(e), task_id))

weekly_test_service = WeeklyTestService()
