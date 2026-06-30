from services.db_service import db_service
from routes.dashboard import get_current_user
# pyrefly: ignore [missing-import]
from flask import Flask

app = Flask(__name__)
with app.test_request_context():
    # Unfortunately get_current_user relies on request.cookies.get
    # Let's just print all users that have semesters
    sems = db_service.query("SELECT user_id, count(*) as count FROM semesters GROUP BY user_id")
    print("Semesters per user:")
    for s in sems:
        print(f"User: {s['user_id']}, Count: {s['count']}")
        
    print("\nUsers that have subjects:")
    subs = db_service.query("SELECT semesters.user_id, count(subjects.id) as count FROM subjects JOIN semesters ON subjects.semester_id = semesters.id GROUP BY semesters.user_id")
    for s in subs:
        print(f"User: {s['user_id']}, Count: {s['count']}")
