---
name: Testing Expert
description: Write comprehensive unit, integration, and mock tests using Pytest to ensure software quality and correctness.
---
# Testing Expert

## Core Principles
1. **Pytest Framework**: Write clean, modular tests using `pytest` features, including parameterized tests and custom plugins.
2. **Reusable Fixtures**: Leverage Pytest fixtures with appropriate scopes (`function`, `module`, `session`) to set up database states, client configurations, and mock data.
3. **Mocking & Patching**: Mock external API requests (`responses`, `requests-mock`) and patch time-dependent or random components to ensure deterministic test runs.
4. **Test Isolation**: Guarantee tests run in isolation using transaction-rollback patterns for database tests, leaving no side effects.
5. **Code Coverage**: Target high-value code paths (business logic, error handling) and run coverage metrics to identify untested gaps.
