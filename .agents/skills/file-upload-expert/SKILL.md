---
name: File Upload Expert
description: Securely handle file uploads, validate file types, enforce size limits, and manage cloud storage.
---
# File Upload Expert

## Core Principles
1. **Strict File Validation**: Validate uploads using magic numbers (file signatures) rather than trusting the user-provided extension or MIME type.
2. **Size & Volume Limits**: Enforce maximum file size restrictions at both the application level and the web server/reverse proxy level.
3. **Input Sanitization**: Sanitize uploaded filenames to prevent path traversal attacks (e.g., using `werkzeug.utils.secure_filename`).
4. **Storage Security**: Store uploaded files outside the web root, or use dedicated cloud object storage (S3, Supabase Storage) with randomized filenames.
5. **Processing Safety**: Isolate and sand-box file processing (e.g., PDF parsing, image resizing) to prevent remote code execution (RCE) or denial of service (DoS).
