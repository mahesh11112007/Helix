import os
import sqlite3
import psycopg2
import psycopg2.extras
# pyrefly: ignore [missing-import]
from supabase import create_client, Client

class DBService:
    def __init__(self):
        # Vercel Supabase Integration automatically injects POSTGRES_URL
        url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or os.getenv("DATABASE_POSTGRES_URL")
        if url and "?" in url:
            # psycopg2 does not support unknown query params like ?supa=... injected by Vercel
            import urllib.parse as urlparse
            parsed = urlparse.urlparse(url)
            query = urlparse.parse_qs(parsed.query)
            # Remove unsupported params
            query.pop("supa", None)
            query.pop("pgbouncer", None)
            new_query = urlparse.urlencode(query, doseq=True)
            url = urlparse.urlunparse(parsed._replace(query=new_query))
        
        self.database_url = url
        self.use_postgres = bool(self.database_url)
        
        # Keep supabase init just in case it's used elsewhere for storage
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.use_supabase = bool(self.supabase_url and self.supabase_key)
        
        if os.environ.get("VERCEL"):
            self.sqlite_db = "/tmp/kiraak_study.db"
        else:
            self.sqlite_db = "kiraak_study.db"
        
        self._init_db()

    def _get_conn(self):
        if self.use_postgres:
            conn = psycopg2.connect(self.database_url)
            return conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            conn = sqlite3.connect(self.sqlite_db)
            conn.row_factory = sqlite3.Row
            return conn, conn.cursor()

    def _translate_schema(self, sql):
        if self.use_postgres:
            return sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY").replace("TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        return sql

    def _init_db(self):
        conn, cursor = self._get_conn()
        
        try:
            # Create Profiles Table
            cursor.execute(self._translate_schema("""
            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE,
                full_name TEXT,
                avatar_url TEXT,
                current_semester_id TEXT,
                study_streak INTEGER DEFAULT 0,
                api_keys TEXT,
                ai_platform TEXT DEFAULT 'nvidia',
                custom_instructions TEXT DEFAULT '',
                password_hash TEXT,
                google_id TEXT UNIQUE,
                last_active TEXT,
                math_learning_level TEXT,
                is_premium BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""))
            
            # Semesters Table
            cursor.execute(self._translate_schema("""
            CREATE TABLE IF NOT EXISTS semesters (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""))
            
            # Subjects Table
            cursor.execute(self._translate_schema("""
            CREATE TABLE IF NOT EXISTS subjects (
                id TEXT PRIMARY KEY,
                semester_id TEXT,
                name TEXT,
                code TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""))
            
            # Units Table
            cursor.execute(self._translate_schema("""
            CREATE TABLE IF NOT EXISTS units (
                id TEXT PRIMARY KEY,
                subject_id TEXT,
                name TEXT,
                number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""))
            
            # Topics Table
            cursor.execute(self._translate_schema("""
            CREATE TABLE IF NOT EXISTS topics (
                id TEXT PRIMARY KEY,
                unit_id TEXT,
                name TEXT,
                order_index INTEGER,
                is_completed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""))
            
            # Files Table
            cursor.execute(self._translate_schema("""
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
            )"""))
            
            # Chat Sessions Table
            cursor.execute(self._translate_schema("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                topic_id TEXT,
                user_id TEXT,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""))
            # System Settings Table
            cursor.execute(self._translate_schema("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key_name TEXT PRIMARY KEY,
                key_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""))
            
            # Chat Messages Table
            cursor.execute(self._translate_schema("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                topic_id TEXT,
                session_id TEXT,
                user_id TEXT,
                role TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""))
            
            # Notes Table
            cursor.execute(self._translate_schema("""
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                topic_id TEXT,
                title TEXT,
                content TEXT,
                is_ai_generated INTEGER DEFAULT 0,
                is_archived INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""))
            
            # Bookmarks Table
            cursor.execute(self._translate_schema("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                topic_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""))
            
            # Flashcards Table
            cursor.execute(self._translate_schema("""
            CREATE TABLE IF NOT EXISTS flashcards (
                id TEXT PRIMARY KEY,
                topic_id TEXT,
                question TEXT,
                answer TEXT,
                difficulty TEXT,
                last_reviewed TEXT,
                next_review TEXT,
                box_number INTEGER DEFAULT 1,
                is_archived INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""))
            
            # Quizzes Table
            cursor.execute(self._translate_schema("""
            CREATE TABLE IF NOT EXISTS quizzes (
                id TEXT PRIMARY KEY,
                topic_id TEXT,
                title TEXT,
                quiz_data TEXT,
                is_archived INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""))
            
            # Quiz Results Table
            cursor.execute(self._translate_schema("""
            CREATE TABLE IF NOT EXISTS quiz_results (
                id TEXT PRIMARY KEY,
                quiz_id TEXT,
                user_id TEXT,
                score INTEGER,
                total_questions INTEGER,
                accuracy REAL,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""))
            
            # Study Sessions Table
            cursor.execute(self._translate_schema("""
            CREATE TABLE IF NOT EXISTS study_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                topic_id TEXT,
                start_time TEXT,
                duration_minutes INTEGER,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""))
            
            # Background tasks
            cursor.execute(self._translate_schema('''
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
            '''))
            
            # User Usage & Limits Table
            cursor.execute(self._translate_schema("""
            CREATE TABLE IF NOT EXISTS user_usage (
                user_id TEXT PRIMARY KEY,
                subscription_tier TEXT DEFAULT 'free',
                study_decks_generated INTEGER DEFAULT 0,
                planner_commands_used INTEGER DEFAULT 0,
                daily_chats INTEGER DEFAULT 0,
                last_chat_date TEXT
            )"""))
            
            # AI Query Semantic Cache Table
            cursor.execute(self._translate_schema("""
            CREATE TABLE IF NOT EXISTS ai_query_cache (
                id SERIAL PRIMARY KEY,
                query_text TEXT,
                normalized_query TEXT,
                ai_response TEXT,
                topic_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""))
            
            # Planner Events Table
            cursor.execute(self._translate_schema("""
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
            )"""))
            
            # Password Reset OTPs Table
            cursor.execute(self._translate_schema("""
            CREATE TABLE IF NOT EXISTS password_reset_otps (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                otp_hash TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""))
            
            # Payment Proofs Table
            cursor.execute(self._translate_schema("""
            CREATE TABLE IF NOT EXISTS payment_proofs (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""))
            
            # Support Requests Table
            cursor.execute(self._translate_schema("""
            CREATE TABLE IF NOT EXISTS support_requests (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                message TEXT NOT NULL,
                ai_response TEXT,
                is_genuine INTEGER DEFAULT 0,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""))
            
            # Clear stale completed/failed tasks on startup to prevent timezone layout loops
            try:
                cursor.execute("DELETE FROM background_tasks WHERE status IN ('completed', 'failed')")
            except Exception:
                pass
                
            # Migration: add math_learning_level to profiles if it doesn't exist
            try:
                cursor.execute("ALTER TABLE profiles ADD COLUMN math_learning_level TEXT")
            except Exception:
                pass
                
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error initializing database schema: {e}")
        finally:
            conn.close()

    def _prepare_query(self, query_str):
        if self.use_postgres:
            return query_str.replace('?', '%s')
        return query_str

    def query(self, query_str, params=(), one=False):
        conn, cursor = self._get_conn()
        try:
            cursor.execute(self._prepare_query(query_str), params)
            rv = cursor.fetchall()
            return (rv[0] if rv else None) if one else rv
        finally:
            conn.close()

    def execute(self, query_str, params=()):
        conn, cursor = self._get_conn()
        try:
            cursor.execute(self._prepare_query(query_str), params)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

db_service = DBService()
