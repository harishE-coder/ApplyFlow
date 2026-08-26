# Changelog

All notable changes to the **ApplyFlow** platform are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2026-08-26 (v1.1 MVP Release)

### ✨ Added
- **AI Interview Intake Engine**:
  - Groq LLaMA 3.3 70B integration for automated parsing of interview invitation emails, rejection updates, and round transitions.
  - Multi-input support: raw text paste, `.eml` email upload, and OCR screenshots.
  - 4-Tier Smart Resume Linking priority matcher (`Resume ID tag` $\rightarrow$ `Candidate Name + Company` $\rightarrow$ `Candidate Name + Role` $\rightarrow$ `Unmatched Application`).
- **Role-Based Hierarchy & Delegation**:
  - `admin`: Global tenant management, client onboarding, recruiter assignments, and audit telemetry.
  - `sub_admin`: Scoped management over delegated clients and recruiters without global access.
  - `employee`: Recruiter workspace, bulk resume uploads, Candidate Studio, AI intake, targets, attendance, and client chat.
  - `client`: Customer portal, candidate pipeline view, status progress tracking, and dedicated recruiter messaging.
- **Cloud Resume Storage & Ingestion**:
  - Google Apps Script Web App integration for reliable Google Drive ingestion and streaming.
  - Dynamic filename tokenizer: automatic extraction of Candidate Name, Hiring Company, Role Designation, and Resume Tags (`TCS_JavaDeveloper_RES101.pdf`).
  - Pre-commit duplicate detection endpoint.
  - Clean binary streaming with inline preview and PDF download protection.
- **Real-Time Dynamic Dashboards & Telemetry**:
  - Recruiter Daily Target Quota widget auto-recalculating in real-time from database queries.
  - Real-time event bus synchronization across UI views (`resume-uploaded`, `application-created`, `application-updated`).
  - Support for $>100\%$ target over-achievement.
  - Dedicated Client Portal dashboard isolating client-scoped candidates only.
- **Real-Time Role-Based Chat**:
  - WebSocket presence, typing indicators, and message broadcasts.
  - Read receipts and unread badge counters.
- **Shift Attendance & Time Tracking**:
  - Recruiter Check-In / Check-Out system with live duration calculation and Admin live roster.
- **Reporting & Data Exports**:
  - Multi-sheet Excel exports (`.xlsx`), CSV client/employee exports, and PDF summary generation.

### 🔄 Changed
- Refactored daily target calculation to query `applications` as the single source of truth for pipeline submission.
- Consolidated client scoping logic to strictly enforce multi-tenant customer isolation across all API routes.
- Standardized date filters to anchor strictly on calendar boundaries.

### 🐛 Fixed
- Resolved Daily Target Quota widget staleness upon bulk resume upload.
- Fixed UTC vs local timezone discrepancies in date range filters.
- Fixed client company deactivation lockout: users belonging to deactivated companies are immediately blocked from logging in.
- Fixed PDF download streaming to guarantee raw `%PDF-1.4` headers without HTML encapsulation.
- Fixed SQLite schema constraints and missing column migrations.
