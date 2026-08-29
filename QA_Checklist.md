# ApplyFlow ATS — Comprehensive QA & Test Verification Checklist

> **Specification Version**: 1.2.0  
> **Testing Scope**: Manual QA, Integration Test Scenarios, Regression Matrices, Edge Verification, and Performance Audits

---

## 1. Authentication & Session Management

- [ ] **AUTH-01 (Happy Path Login)**: Verify login with valid Super Admin email and password. Confirm HTTP-only `access_token` and `refresh_token` cookies are set.
- [ ] **AUTH-02 (Invalid Credentials)**: Verify login with incorrect password. Confirm HTTP 401 Unauthorized is returned and error toast renders.
- [ ] **AUTH-03 (Inactive Account Gating)**: Set `users.is_active = false`. Attempt login with valid credentials. Verify login is blocked.
- [ ] **AUTH-04 (Silent Token Refresh)**: Expire `access_token` after 60 minutes. Make authenticated API request. Confirm Axios response interceptor triggers `POST /api/auth/refresh` and completes original request without user redirect.
- [ ] **AUTH-05 (Universal Bootstrap)**: Verify `GET /api/auth/bootstrap` returns user profile, role dashboard, unread notifications, and unread chat count in a single request (< 100ms).
- [ ] **AUTH-06 (Logout Session Termination)**: Verify `POST /api/auth/logout` clears both auth cookies and redirects user to `/login`.

---

## 2. Bulk Resume Ingestion & Storage Engine

- [ ] **RES-01 (Recruiter Single Upload)**: Upload a single valid PDF formatted as `ABCStaffing_TCS_JavaLead_RahulKumar.pdf`. Confirm candidate is ingested and visible in candidate bank.
- [ ] **RES-02 (Batch Upload 1 to 50+ Files)**: Upload 50 valid PDFs in a single drag-and-drop batch. Verify progress bar tracks accurately and all 50 records commit successfully.
- [ ] **RES-03 (Admin Upload Protection)**: Log in as Super Admin and attempt to access `/upload`. Confirm immediate redirect to `/dashboard` with permission denied notice.
- [ ] **RES-04 (Strict Service Client Verification - Match)**: Select client *ABC Staffing*. Drop file `ABCStaffing_Google_SDE2.pdf`. Confirm status is `ServiceClient Verified` (Green).
- [ ] **RES-05 (Strict Service Client Verification - Mismatch)**: Select client *ABC Staffing*. Drop file `NextHire_Google_SDE2.pdf`. Confirm status is `ServiceClient Mismatch` (Red).
- [ ] **RES-06 (Natural Candidate Resume Filename)**: Drop file `Suresh_resume (2).pdf`. Confirm tokenizer auto-assigns selected Service Client and cleans candidate name to `"Suresh"`.
- [ ] **RES-07 (Pre-Commit Duplicate Detection)**: Drop a file matching an already ingested candidate. Confirm row is highlighted in Amber (`Duplicate Exists`) with existing record match.
- [ ] **RES-08 (Dual Storage Sync)**: Upload file with Google Apps Script configured. Confirm local disk write succeeds instantly (< 5ms) and background worker syncs file to Google Drive.
- [ ] **RES-09 (Zero-Leakage PDF Inline Stream)**: Open candidate in Candidate Studio. Verify PDF renders inline with `application/pdf` header and zero external URL leakage.
- [ ] **RES-10 (Protected PDF Download)**: Click download button on candidate card. Verify raw binary PDF streams with `Content-Disposition: attachment`.
- [ ] **RES-11 (Resume Deletion RBAC)**: Verify Super Admin can delete any resume; Recruiter can only delete their own uploads; Client cannot delete resumes.

---

## 3. Groq AI Email Interview Intake & 4-Tier Matching

- [ ] **AI-01 (Interview Invitation Parsing)**: Paste interview email for Java Lead at TCS. Click Analyze. Verify Groq LLaMA 3.3 extracts Candidate, Company, Role, Status, Round, and Date accurately.
- [ ] **AI-02 (Spam & Marketing Email Rejection)**: Paste marketing newsletter or invoice email. Click Analyze. Confirm decision is `not_related` (`is_interview_mail: false`) and 0 database writes occur.
- [ ] **AI-03 (Tier 1 Smart Matching - Tag)**: Paste email mentioning `"Resume ID: RES101"`. Verify matching links to exact resume with `match_priority: 1`.
- [ ] **AI-04 (Tier 2 Smart Matching - Name + Company)**: Paste email with `"Rahul Kumar"` interviewing at `"TCS"`. Verify matching links to existing resume with `match_priority: 2`.
- [ ] **AI-05 (Tier 3 Smart Matching - Name + Role)**: Paste email with `"Priya Sundaram"` for `"Frontend Engineer"`. Verify matching links with `match_priority: 3`.
- [ ] **AI-06 (Tier 4 Smart Matching - Unmatched Fallback)**: Paste email for candidate not in candidate bank. Confirm application is created with `resume_id = null` without throwing errors.
- [ ] **AI-07 (Human Confirmation Execution)**: Review AI extraction card, edit round name, and click Confirm. Confirm application advances, event is logged in timeline, update posts to Client Chat, and notification is sent.
- [ ] **AI-08 (Multi-Channel Intake - EML Upload)**: Upload `.eml` file. Verify email headers and body text are cleanly extracted and analyzed.
- [ ] **AI-09 (Multi-Channel Intake - Screenshot OCR)**: Upload image screenshot of interview update. Verify OCR extracts text and parses entities.

---

## 4. Daily Targets & Quotas Engine

- [ ] **TGT-01 (Set Daily Target)**: As Super Admin, assign Recruiter daily target of 25 for *ABC Staffing*. Verify target saves with `status: "active"`.
- [ ] **TGT-02 (Dynamic Quota Calculation)**: Submit 14 applications as Recruiter. Verify target donut shows `14 / 25` (56.0% Progress Orange).
- [ ] **TGT-03 (Target 100%+ Over-Achievement)**: Submit 28 applications against a target of 25. Verify target donut shifts to Success Emerald (`112%`) with `+3 Over-achieved` badge.
- [ ] **TGT-04 (Target Status Pausing)**: Pause active target. Verify paused target is excluded from live quota calculations.
- [ ] **TGT-05 (Target Historical Deletion Rule)**: Attempt to delete target whose `effective_date < TODAY`. Confirm deletion is blocked with HTTP 400.

---

## 5. Shift Attendance & Session Timer

- [ ] **ATT-01 (Check-In Work Session)**: As Recruiter, click "Check In". Confirm session timer starts ticking (`00:00:01`) and attendance record is created.
- [ ] **ATT-02 (Check-Out Work Session)**: Click "Check Out". Confirm timer stops and `total_hours` is formatted (e.g. `"7h 30m"`).
- [ ] **ATT-03 (Duplicate Check-In Guard)**: Attempt to check in twice on the same day. Verify second check-in is rejected gracefully.
- [ ] **ATT-04 (Super Admin Attendance Roster)**: As Super Admin, inspect Live Attendance Summary. Confirm active and checked-out staff counts match actual records.

---

## 6. Real-Time Role-Based Chat

- [ ] **CHAT-01 (Room Access Scoping)**: Verify Recruiter sees only assigned client rooms; Client user sees only their own room.
- [ ] **CHAT-02 (Live WebSocket Messaging)**: Send message from Recruiter window. Confirm message appears in Client window instantly without page reload.
- [ ] **CHAT-03 (Candidate Resume Sharing)**: Open resume share modal in chat, select candidate `RES101`, and share. Verify interactive candidate card renders in conversation stream.
- [ ] **CHAT-04 (Typing Indicator)**: Type in message input. Confirm `"User is typing..."` appears in remote participant's window.
- [ ] **CHAT-05 (Cursor Read Receipts)**: Read message in room. Verify read receipt (`✓✓ Read`) updates for sender.
- [ ] **CHAT-06 (Deactivated Client Read-Only Chat)**: Deactivate client. Confirm chat input is disabled and marked read-only.

---

## 7. Multi-Format Reports & Data Exports

- [ ] **RPT-01 (Excel Master Export)**: Download Excel report via `GET /api/reports/excel`. Open in Microsoft Excel; verify multiple sheets, formula calculations, and styling formatting.
- [ ] **RPT-02 (PDF Executive Summary)**: Generate PDF report via `GET /api/reports/pdf`. Verify branded styling, candidate stats, and KPI summaries.
- [ ] **RPT-03 (CSV Operational Exports)**: Export Active Clients, Inactive Employees, and Ended Targets. Verify valid CSV formatting.

---

## 8. Role-Based Access Control & Security

- [ ] **SEC-01 (IDOR Candidate Protection)**: Attempt to fetch resume ID belonging to *Client B* while authenticated as *Client A*. Verify HTTP 403 Forbidden.
- [ ] **SEC-02 (Sub-Admin Scoped Isolation)**: Log in as Sub-Admin. Confirm only assigned clients and recruiters appear in dashboards and search dropdowns.
- [ ] **SEC-03 (Safe Deletion Protection)**: Attempt to delete Service Client with existing resumes and applications. Confirm deletion is prevented with HTTP 400 error.
