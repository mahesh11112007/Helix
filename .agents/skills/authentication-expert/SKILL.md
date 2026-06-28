---
name: Authentication Expert
description: Implement secure user authentication, authorization, token-based sessions, and access control models.
---
# Authentication Expert

## Core Principles
1. **Token-Based Sessions**: Securely generate, verify, and rotate JSON Web Tokens (JWT) or opaque session tokens. Enforce secure cookie attributes (`HttpOnly`, `Secure`, `SameSite=Strict`).
2. **OAuth 2.0 & OIDC**: Integrate third-party social logins (Google, GitHub, etc.) conforming to OAuth 2.0 and OpenID Connect specifications.
3. **Access Control Models**: Implement Role-Based Access Control (RBAC) or Attribute-Based Access Control (ABAC) to enforce granular permissions.
4. **Password Security**: Use strong, slow hashing algorithms (like bcrypt or Argon2) with custom salts for storing passwords.
5. **MFA & Recovery**: Design secure Multi-Factor Authentication (MFA) flows and secure, time-sensitive password reset/recovery processes.
