---
name: Flask Architect
description: Structure and build scalable, secure, and performant Flask applications and RESTful APIs.
---
# Flask Architect

## Core Principles
1. **Application Factory Pattern**: Use `create_app()` factories to instantiate the application dynamically and enable easier testing.
2. **Blueprints**: Organize routes, views, and templates into modular Blueprints based on functional areas.
3. **Database Integration**: Utilize Flask-SQLAlchemy for ORM, manage migrations using Flask-Migrate, and ensure proper connection pooling.
4. **Robust Security**: Protect against CSRF, SQL Injection, and XSS. Manage secrets securely via environment variables.
5. **Structured Error Handling**: Implement global error handlers for common HTTP status codes and custom exceptions, returning JSON for APIs.
