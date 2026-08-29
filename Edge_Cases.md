# ApplyFlow ATS — Real-World Edge Cases & Failure Recovery Guide

> **Specification Version**: 1.2.0  
> **Target Audience**: Principal Engineers, Site Reliability Engineers (SREs), QA Architects, Operations Leads

---

## 1. File Ingestion & Resume Parser Edge Cases

### 1.1 Non-Standard and Heavily Noisy Filenames
- **Scenario**: Candidate submits file named `Copy of John_Doe_Resume_Final(2) (1)_v3_edited.pdf`.
- **System Handling**:
  - `_clean_candidate_name()` regex strips noise tokens: `copy`, `resume`, `cv`, `final`, `v3`, `(1)`, `(2)`, `_`, `-`.
  - Converts camelCase to spaced words and title-cases the string: `"John Doe"`.
  - Auto-assigns selected Service Client and marks `ServiceClient Verified`.

### 1.2 Multi-Segment Structured Filenames
- **Scenario**: `ABCStaffing_TataConsultancyServices_SeniorLeadArchitect_RES9021.pdf`.
- **System Handling**:
  - Segment 0: Checked against `ABC Staffing` (Matches $\rightarrow$ Verified).
  - Segment 1: `Tata Consultancy Services` $\rightarrow$ Target Company.
  - Segment 2: `Senior Lead Architect` $\rightarrow$ Role.
  - Segment 3: `RES9021` $\rightarrow$ Resume ID Tag.

### 1.3 Large Batch Ingestion (100+ PDFs)
- **Scenario**: Recruiter drops 120 PDF resumes simultaneously on a low-end laptop.
- **System Handling**:
  - Frontend uses **progressive virtual rendering**: renders first 20 items immediately, then progressively adds 50 items per 50ms interval to prevent DOM freezing.
  - Synchronously writes files to local disk `./uploads/` (< 5ms total) and queues asynchronous background tasks for Google Apps Script sync.

### 1.4 Corrupted or Zero-Byte PDF Uploads
- **Scenario**: Upload contains 0-byte file or non-PDF binary masquerading as PDF.
- **System Handling**:
  - Verifies file magic bytes start with `%PDF-`.
  - Rejects malformed files immediately with HTTP 400 and clear error message in ingestion queue.

---

## 2. Google Apps Script & Cloud Storage Edge Cases

### 2.1 Google Apps Script Rate Limits & Network Timeouts
- **Scenario**: Google Apps Script API experiences cold start or quota exhaustion (HTTP 429 / Timeout).
- **System Handling**:
  - FastAPI storage engine logs warning and **falls back immediately to local disk storage** (`./uploads/`).
  - Resume record remains 100% functional with local file ID (`file_...`).
  - Local files are served seamlessly via `GET /api/resumes/{id}/preview` and `/download`.
  - Background worker retries Google Drive sync once external API recovers.

### 2.2 Google Drive HTML Redirect Response
- **Scenario**: Google Apps Script returns HTML with `window.location = "..."` redirect script instead of raw binary.
- **System Handling**:
  - `get_file_bytes()` checks content type. If HTML is detected, parses redirect URL via regex and streams binary target.
  - If external fetch fails, falls back to `_generate_valid_pdf()` ATS container, guaranteeing the client always receives a valid PDF binary stream.

---

## 3. Groq AI Email Intake & Parsing Edge Cases

### 3.1 Marketing Newsletters, Invoices, and Spam
- **Scenario**: Recruiter pastes AWS billing invoice or LinkedIn marketing newsletter into AI Inbox.
- **System Handling**:
  - Groq LLaMA 3.3 evaluates `is_interview_mail: false` and `decision: "not_related"`.
  - UI displays an amber warning banner: `"This email is not a recruitment/interview update. Ignored."`.
  - **Zero database rows are written**, preventing spam from polluting candidate pipelines.

### 3.2 Candidate Name Collisions in Same Client
- **Scenario**: Two candidates named `"Rahul Kumar"` exist in *ABC Staffing*, one for *TCS* and one for *Infosys*.
- **System Handling**:
  - Priority 1 checks exact `resume_id_tag` (e.g. `RES101`).
  - Priority 2 matches Candidate Name + Target Company (`"Rahul Kumar"` + `"TCS"`).
  - Isolates match strictly to the intended candidate record.

### 3.3 Completely Unmatched Candidates (Priority 4 Fallback)
- **Scenario**: Interview update arrives for a candidate sourced externally who does not exist in the candidate bank.
- **System Handling**:
  - 4-Tier matcher creates an application record with `resume_id = null`.
  - Candidate name, company, and role are preserved directly on the `applications` record.
  - Recruiter can manually link a resume PDF later via 1-click binding without losing the interview schedule.

---

## 4. Quota Engine, Timezones & Date Filters

### 4.1 Cross-Midnight Shift Sessions
- **Scenario**: Recruiter checks in at 10:00 PM on Aug 27 and checks out at 02:00 AM on Aug 28.
- **System Handling**:
  - Attendance record is tied to `work_date = 2026-08-27` (the date of check-in).
  - Check-out accurately calculates total duration across midnight (4 hours).

### 4.2 Over-Achievement (> 100% Daily Target)
- **Scenario**: Recruiter submits 35 applications against a daily target of 25.
- **System Handling**:
  - Progress Ring renders 140% with Success Emerald color and dynamic SVG stroke.
  - `remaining_target` is capped at `0` ($\max(\text{Target} - \text{Done}, 0)$), preventing negative remaining work numbers.

---

## 5. Concurrency & Real-Time Chat

### 5.1 Simultaneous Message Delivery
- **Scenario**: Recruiter and Client send messages at the exact same millisecond in a chat room.
- **System Handling**:
  - Database commits both messages with microsecond-precision `created_at` timestamps.
  - WebSocket broadcasts messages sequentially; frontend appends rows deterministically based on timestamp ordering.

### 5.2 Client Account Deactivation with Active Chat
- **Scenario**: Admin deactivates *ABC Staffing* while recruiter has the chat window open.
- **System Handling**:
  - `POST /api/chat/rooms/{id}/messages` rejects new messages with HTTP 403.
  - Chat input transitions to disabled state with banner: `"This customer account is deactivated. Chat is in read-only mode."`.
