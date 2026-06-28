import os
import sqlite3
from supabase import create_client, Client

class DBService:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.use_supabase = bool(self.supabase_url and self.supabase_key)
        self.sqlite_db = "kiraak_study.db"
        
        if not self.use_supabase:
            self._init_sqlite()

    def _get_sqlite_conn(self):
        conn = sqlite3.connect(self.sqlite_db)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite(self):
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        
        # Create Profiles Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            full_name TEXT,
            avatar_url TEXT,
            current_semester_id TEXT,
            study_streak INTEGER DEFAULT 0,
            api_keys TEXT,
            ai_platform TEXT DEFAULT 'custom',
            custom_instructions TEXT DEFAULT '',
            password_hash TEXT,
            google_id TEXT UNIQUE,
            last_active TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Add ai_platform column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE profiles ADD COLUMN ai_platform TEXT DEFAULT 'custom'")
        except sqlite3.OperationalError:
            pass
            
        # Add custom_instructions column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE profiles ADD COLUMN custom_instructions TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass

        # Add password_hash column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE profiles ADD COLUMN password_hash TEXT")
        except sqlite3.OperationalError:
            pass
            
        # Add google_id column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE profiles ADD COLUMN google_id TEXT")
        except sqlite3.OperationalError:
            pass
        
        # Semesters Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS semesters (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Subjects Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id TEXT PRIMARY KEY,
            semester_id TEXT,
            name TEXT,
            code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Units Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS units (
            id TEXT PRIMARY KEY,
            subject_id TEXT,
            name TEXT,
            number INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Topics Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id TEXT PRIMARY KEY,
            unit_id TEXT,
            name TEXT,
            order_index INTEGER,
            is_completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Files Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id TEXT PRIMARY KEY,
            topic_id TEXT,
            name TEXT,
            file_path TEXT,
            file_type TEXT,
            file_size INTEGER,
            is_favorite INTEGER DEFAULT 0,
            is_archived INTEGER DEFAULT 0,
            tags TEXT,
            ocr_text TEXT,
            summary TEXT,
            keywords TEXT,
            ai_notes TEXT,
            flashcards TEXT,
            mcqs TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Chat Sessions Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY,
            topic_id TEXT,
            user_id TEXT,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Chat Messages Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            topic_id TEXT,
            session_id TEXT,
            user_id TEXT,
            role TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Add session_id column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE chat_messages ADD COLUMN session_id TEXT")
        except sqlite3.OperationalError:
            pass
        
        # Notes Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY,
            topic_id TEXT,
            title TEXT,
            content TEXT,
            is_ai_generated INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Bookmarks Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookmarks (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            topic_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Flashcards Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS flashcards (
            id TEXT PRIMARY KEY,
            topic_id TEXT,
            question TEXT,
            answer TEXT,
            difficulty TEXT,
            last_reviewed TEXT,
            next_review TEXT,
            box_number INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Quizzes Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            id TEXT PRIMARY KEY,
            topic_id TEXT,
            title TEXT,
            quiz_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Quiz Results Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_results (
            id TEXT PRIMARY KEY,
            quiz_id TEXT,
            user_id TEXT,
            score INTEGER,
            total_questions INTEGER,
            accuracy REAL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Study Sessions Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS study_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            topic_id TEXT,
            start_time TEXT,
            duration_minutes INTEGER,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Background tasks
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS background_tasks (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                task_type TEXT,
                status TEXT,
                total_items INTEGER DEFAULT 0,
                completed_items INTEGER DEFAULT 0,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User Usage & Limits Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_usage (
            user_id TEXT PRIMARY KEY,
            subscription_tier TEXT DEFAULT 'free',
            study_decks_generated INTEGER DEFAULT 0,
            planner_commands_used INTEGER DEFAULT 0,
            daily_chats INTEGER DEFAULT 0,
            last_chat_date TEXT,
            FOREIGN KEY(user_id) REFERENCES profiles(id)
        )""")
        
        # AI Query Semantic Cache Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_query_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_text TEXT,
            normalized_query TEXT,
            ai_response TEXT,
            topic_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Planner Events Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS planner_events (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            title TEXT,
            description TEXT,
            start_time TEXT,
            end_time TEXT,
            event_type TEXT,
            is_completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Bookmarks Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookmarks (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            topic_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Password Reset OTPs Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_otps (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            otp_hash TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Clear stale completed/failed tasks on startup to prevent timezone layout loops
        try:
            cursor.execute("DELETE FROM background_tasks WHERE status IN ('completed', 'failed')")
        except sqlite3.OperationalError:
            pass
            
        conn.commit()
        conn.close()
        
        # Run safe migrations for existing databases
        self._migrate_schema()

    def _migrate_schema(self):
        """Safely add new columns to existing tables without losing data."""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        
        migrations = [
            ("notes", "is_archived", "INTEGER DEFAULT 0"),
            ("flashcards", "is_archived", "INTEGER DEFAULT 0"),
            ("quizzes", "is_archived", "INTEGER DEFAULT 0"),
        ]
        
        for table, column, col_type in migrations:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            except Exception:
                pass  # Column already exists
        
        conn.commit()
        conn.close()

    # Generic Helper Methods for CRUD that fallback automatically
    def query(self, query_str, params=(), one=False):
        if self.use_supabase:
            # We will implement dynamic supabase queries or execute RPC/direct query requests.
            # However, since Supabase utilizes a standard Client SDK, we will offer specialized methods
            # and use standard query wrappers if possible. Let's write a standard interface.
            pass
        else:
            conn = self._get_sqlite_conn()
            cursor = conn.cursor()
            cursor.execute(query_str, params)
            rv = cursor.fetchall()
            conn.close()
            return (rv[0] if rv else None) if one else rv

    def execute(self, query_str, params=()):
        if not self.use_supabase:
            conn = self._get_sqlite_conn()
            cursor = conn.cursor()
            cursor.execute(query_str, params)
            conn.commit()
            conn.close()

db_service = DBService()
