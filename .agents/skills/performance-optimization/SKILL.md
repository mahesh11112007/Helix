---
name: Performance Optimization Expert
description: Improve application speed, implement caching strategies, manage async execution, and optimize API endpoints.
---
# Performance Optimization Expert

## Core Principles
1. **Caching Strategies**: Implement multi-tier caching (in-memory, Redis, HTTP gateway caching) with precise TTLs and invalidation policies.
2. **Asynchronous Execution**: Offload heavy computations, email sending, and long-running I/O to background workers (e.g., Celery, Redis Queue).
3. **API Payload Optimization**: Minimize payload sizes using Gzip/Brotli compression, selective field inclusion, and paginated responses.
4. **Database Query Minimization**: Eliminate N+1 query problems using eager loading (`joinedload` in SQLAlchemy) and profile execution times.
5. **Profiling & Monitoring**: Utilize profiling tools (e.g., cProfile, APM agents) to isolate CPU-bound or memory-heavy code paths.
