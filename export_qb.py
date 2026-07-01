import json
from services.db_service import db_service

def export_questions():
    rows = db_service.query('SELECT * FROM question_bank')
    
    # SQLite rows might be Row objects, convert to dict
    data = [dict(r) for r in rows]
    
    with open('question_bank_export.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
        
    print(f"Successfully exported {len(data)} questions to question_bank_export.json")

if __name__ == "__main__":
    export_questions()
