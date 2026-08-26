# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.1.x   | :white_check_mark: |
| < 1.1.0 | :x:                |

---

## 🔒 Security Architecture

ApplyFlow implements robust security controls across all architectural layers:

1. **Authentication & Session Security**:
   - HTTP-only, `SameSite=Lax` cookies for JWT storage protecting against Cross-Site Scripting (XSS) token theft.
   - Dual-token lifecycle: Short-lived access tokens (60 min) with cryptographically validated refresh token rotation (7 days).
   - Instant account invalidation on client company deactivation or recruiter offboarding.

2. **Authorization & Multi-Tenant Boundary Enforcement**:
   - Role-Based Access Control (RBAC) covering `admin`, `sub_admin`, `employee`, and `client`.
   - Insecure Direct Object Reference (IDOR) prevention: Customers can never query, preview, or download resumes or applications belonging to foreign clients.
   - Admin upload boundary: Administrators cannot upload resumes directly, enforcing strict recruiter accountability.

3. **Input Sanitization & Injection Prevention**:
   - SQLAlchemy parameterized queries preventing SQL injection across all filter, search, and pagination parameters.
   - Strict Pydantic model validation on all HTTP request bodies and URL query parameters.

---

## 🚨 Reporting a Vulnerability

If you discover a security vulnerability in ApplyFlow, please report it responsibly:

- **Email**: security@applyflow.com
- **Response Time**: You will receive an initial response within 24 hours.
- Please do **not** open a public issue on GitHub for security vulnerabilities.

Include detailed reproduction steps, payload examples, and affected endpoint URLs in your advisory.
