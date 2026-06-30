import threading
import uuid
import traceback
from datetime import datetime
from services.db_service import db_service
from services.ai_service import ai_service

class TaskService:
    def __init__(self):
        pass
        
    def start_generate_materials_task(self, user_id, topics_to_generate, run_sync=False):
        """
        Spawns a background thread (or runs synchronously) to generate materials for a list of topics.
        Returns the task_id.
        """
        task_id = str(uuid.uuid4())
        total_items = len(topics_to_generate)
        
        # Insert initial task record
        db_service.execute(
            """INSERT INTO background_tasks (id, user_id, task_type, status, total_items, completed_items, message)
               VALUES (?, ?, 'generate_study_materials', 'pending', ?, 0, 'Task queued')""",
            (task_id, user_id, total_items)
        )
        
        if run_sync:
            self._generate_materials_worker(task_id, topics_to_generate)
        else:
            # Start thread
            thread = threading.Thread(
                target=self._generate_materials_worker,
                args=(task_id, topics_to_generate)
            )
            thread.daemon = True
            thread.start()
            
        return task_id
        
    def _generate_materials_worker(self, task_id, topics_to_generate):
        try:
            # Update status to processing
            db_service.execute(
                "UPDATE background_tasks SET status = 'processing', message = 'Generating materials...', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (task_id,)
            )
            
            # Fetch user_id from task
            task = db_service.query("SELECT user_id FROM background_tasks WHERE id = ?", (task_id,), one=True)
            user_id = task["user_id"] if task else None
            
            # Retrieve API key and config from profiles table
            key = None
            base_url = None
            chat_model = None
            custom_instr = ""
            
            if user_id:
                profile = db_service.query("SELECT api_keys, ai_platform, custom_instructions, math_learning_level, is_premium FROM profiles WHERE id = ?", (user_id,), one=True)
                if profile:
                    profile = dict(profile)
                if profile and profile["api_keys"]:
                    key = profile["api_keys"]
                    platform = profile["ai_platform"] or "custom"
                    custom_instr = profile["custom_instructions"] or ""
                    math_learning_level = profile.get("math_learning_level") or ""
                    is_premium = bool(profile.get("is_premium"))
                    
                    import os
                    if platform == "openai":
                        base_url = "https://api.openai.com/v1"
                        chat_model = "gpt-4o-mini"
                    elif platform == "gemini":
                        base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
                        chat_model = "gemini-1.5-flash"
                    elif platform == "groq":
                        base_url = "https://api.groq.com/openai/v1"
                        chat_model = "llama-3.3-70b-versatile"
                    elif platform == "xai":
                        base_url = "https://api.x.ai/v1"
                        chat_model = "grok-beta"
                    elif platform == "custom":
                        base_url = os.getenv("CUSTOM_AI_BASE_URL", "http://127.0.0.1:8000/v1")
                        chat_model = os.getenv("CUSTOM_AI_MODEL", "Qwen-1.5-4B-Chat-GGUF")
                    else:
                        base_url = "https://integrate.api.nvidia.com/v1"
                        chat_model = "meta/llama-3.1-8b-instruct"
                else:
                    # Fallback to system default config
                    key, base_url, chat_model, _ = ai_service._get_config()
                    if profile and profile.get("custom_instructions"):
                        custom_instr = profile["custom_instructions"]
                    is_premium = bool(profile.get("is_premium")) if profile else False
            else:
                is_premium = False
            
            completed = 0
            
            import time
            for topic_data in topics_to_generate:
                # API Limit Queue logic for free users
                if not is_premium and completed > 0 and completed % 15 == 0:
                    db_service.execute(
                        "UPDATE background_tasks SET status = 'processing', message = 'Waiting 15 minutes due to API rate limits (15 topics generated). Please do not close this window.', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (task_id,)
                    )
                    time.sleep(900)  # Wait 15 minutes
                    db_service.execute(
                        "UPDATE background_tasks SET status = 'processing', message = 'Resuming generation...', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (task_id,)
                    )
                
                # Dynamic Key Rotation for Premium Users using Admin Pool
                if is_premium and (not profile or not profile.get("api_keys")):
                    key, base_url, chat_model, _ = ai_service._get_config()
                if isinstance(topic_data, (tuple, list)):
                    tid = topic_data[0]
                    tname = topic_data[1]
                    sname = topic_data[2] if len(topic_data) > 2 else ""
                else:
                    topic_dict = dict(topic_data) if not isinstance(topic_data, dict) else topic_data
                    tid = topic_dict.get("id")
                    tname = topic_dict.get("name")
                    sname = topic_dict.get("subject_name", "")
                
                # Check if task was cancelled by user
                task_status = db_service.query("SELECT status FROM background_tasks WHERE id = ?", (task_id,), one=True)
                if task_status and task_status["status"] == "cancelled":
                    print(f"Task {task_id} cancelled by user, aborting worker.")
                    return
                    
                try:
                    topic_custom_instr = custom_instr
                    if "math" in sname.lower() and profile and profile.get("math_learning_level"):
                        level = profile["math_learning_level"]
                        if level == "beginner":
                            topic_custom_instr += "\n[MATH STUDENT LEVEL: BEGINNER] Use very simple language. Explain every symbol before using it. Assume no prior knowledge. Show every calculation step. Use many worked examples and diagrams. Introduce mathematical terminology gradually. Frequently check understanding."
                        elif level == "intermediate":
                            topic_custom_instr += "\n[MATH STUDENT LEVEL: INTERMEDIATE] Skip only obvious basics. Focus on conceptual understanding. Explain formulas and their derivations. Include standard exam questions. Provide medium-difficulty practice. Point out common mistakes."
                        elif level == "advanced":
                            topic_custom_instr += "\n[MATH STUDENT LEVEL: ADVANCED] Keep explanations concise but complete. Include mathematical proofs where appropriate. Show multiple solving methods. Teach shortcuts after the standard method. Include higher-order thinking questions. Add Olympiad/competitive-level problems. Explain links to other mathematical topics."

                    materials = ai_service.generate_topic_materials_for_name(
                        tname, 
                        subject_name=sname, 
                        key=key, 
                        base_url=base_url, 
                        chat_model=chat_model, 
                        custom_instr=topic_custom_instr
                    )
                    
                    # Check if generation failed
                    if materials.get("_generation_failed"):
                        db_service.execute(
                            "UPDATE background_tasks SET status = 'failed', message = 'AI generation failed for this topic. Please try again.', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                            (task_id,)
                        )
                        print(f"Generation failed for topic: {tname}")
                        completed += 1
                        continue
                    
                    # Save notes
                    if materials.get("notes"):
                        note_id = str(uuid.uuid4())
                        db_service.execute(
                            """INSERT INTO notes (id, topic_id, title, content, is_ai_generated, is_archived)
                               VALUES (?, ?, ?, ?, 1, 0)""",
                            (note_id, tid, f"AI Notes: {tname}", materials["notes"])
                        )

                    # Save flashcards
                    for card in materials.get("flashcards", []):
                        card_id = str(uuid.uuid4())
                        db_service.execute(
                            """INSERT INTO flashcards (id, topic_id, question, answer, difficulty, box_number, is_archived)
                               VALUES (?, ?, ?, ?, 'medium', 1, 0)""",
                            (card_id, tid, card["question"], card["answer"])
                        )

                    # Save Revision Summary
                    if materials.get("summary"):
                        summary_id = str(uuid.uuid4())
                        db_service.execute(
                            """INSERT INTO notes (id, topic_id, title, content, is_ai_generated, is_archived)
                               VALUES (?, ?, ?, ?, 1, 0)""",
                            (summary_id, tid, f"AI Revision Summary: {tname}", materials["summary"])
                        )

                    # Save quiz
                    quiz_data = materials.get("quizzes", materials.get("quiz", []))
                    if quiz_data:
                        import json
                        quiz_id = str(uuid.uuid4())
                        db_service.execute(
                            """INSERT INTO quizzes (id, topic_id, title, quiz_data, is_archived)
                               VALUES (?, ?, ?, ?, 0)""",
                            (quiz_id, tid, f"AI MCQ Quiz: {tname}", json.dumps(quiz_data))
                        )
                except Exception as e:
                    print(f"Error generating material for topic {tname}: {e}")
                    # Continue with other topics
                
                completed += 1
                db_service.execute(
                    "UPDATE background_tasks SET completed_items = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (completed, task_id)
                )
                
            # Finish task  
            final_status = db_service.query("SELECT status FROM background_tasks WHERE id = ?", (task_id,), one=True)
            if final_status and final_status["status"] != "failed":
                db_service.execute(
                    "UPDATE background_tasks SET status = 'completed', message = 'Generation complete!', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (task_id,)
                )
            
        except Exception as e:
            traceback.print_exc()
            db_service.execute(
                "UPDATE background_tasks SET status = 'failed', message = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (str(e), task_id)
            )

task_service = TaskService()
