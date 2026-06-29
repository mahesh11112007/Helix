import os
from flask import Flask
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "supersecretkey")
    
    # Configure Uploads
    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "../uploads")
    try:
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    except OSError:
        app.config["UPLOAD_FOLDER"] = "/tmp/uploads"
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.files import files_bp
    from routes.planner import planner_bp
    from routes.study import study_bp
    from routes.billing import billing_bp
    from routes.chat import chat_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(planner_bp)
    app.register_blueprint(study_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(chat_bp)
    
    # Streak updater moved to specific actions in routes/study.py
    
    # Simple global context processor for user sessions
    @app.context_processor
    def inject_user():
        from flask import session
        from services.ai_service import ai_service
        is_invalid = session.get("api_key_invalid", False)
        return {
            "current_user": {
                "id": session.get("user_id"),
                "email": session.get("email"),
                "full_name": session.get("full_name")
            } if "user_id" in session else None,
            "has_api_key": bool(ai_service.api_key) and not is_invalid,
            "api_key_invalid": is_invalid
        }

    return app

app = create_app()
