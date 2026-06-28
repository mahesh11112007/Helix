---
name: Flask Expert
description: Structure and build scalable, secure, and performant Flask applications and RESTful APIs.
---
# Flask Expert

## Core Principles
1. **Application Factory Pattern**: Use `create_app()` factory patterns to dynamically initialize applications, making configuration, testing, and multiple instances clean and robust.
2. **Modular Blueprints**: Organize routes, views, static files, and templates into cohesive Blueprints based on functional domains (e.g., auth, API, dashboard).
3. **Middleware & Decorators**: Implement custom decorators for cross-cutting concerns like authentication, role checking, request validation, and rate limiting.
4. **Request & Response Cycle**: Handle request payloads safely, use `jsonify` for standard API responses, and implement custom JSON encoders if necessary.
5. **Global Error Handling**: Utilize `@app.errorhandler` or `@blueprint.app_errorhandler` to catch exceptions globally and return unified error formats (e.g., RFC 7807 problem details).
