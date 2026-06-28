---
name: API Integration Expert
description: Integrate third-party APIs, handle rate limiting, retry mechanisms, and manage external webhooks.
---
# API Integration Expert

## Core Principles
1. **Robust HTTP Clients**: Build wrapper classes using modern HTTP libraries (e.g., `requests`, `httpx`), utilizing connection pooling and proper timeout settings.
2. **Resilience Patterns**: Implement retry mechanisms with exponential backoff and jitter, and apply circuit breakers to prevent cascading failures.
3. **Rate Limit Handling**: Parse rate limit headers (`X-RateLimit-*`) and handle `429 Too Many Requests` responses gracefully.
4. **Webhook Security**: Validate signature headers on incoming webhooks to verify origin and prevent replay attacks.
5. **Structured Payloads**: Parse and validate external API responses using schemas (e.g., Pydantic) to ensure data contract compliance.
