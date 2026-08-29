# ApplyFlow: Complete Features, Rules, and Module Guide

> Canonical working description of the ApplyFlow recruitment workspace. This document describes the behavior implemented in the repository, not only the original product idea.

## 1. What ApplyFlow Is

ApplyFlow is an internal recruitment-agency operating system. It connects four business actors:

- **Super Admin**: owns the whole platform and company-wide operations.
- **Sub-Admin**: manages only the clients and recruiters assigned to them.
- **Employee / Recruiter**: uploads candidate resumes, submits applications, processes interview updates, and communicates with clients.
- **Service Client**: a customer of the recruitment agency. The client sees its own candidates, applications, activity, and recruiter conversations.

The system deliberately separates a **Service Client** from a **Hiring Company**:

- A Service Client is the staffing customer that receives recruitment services.
- A Hiring Company is the employer where the candidate may work, such as TCS, Amazon, or Google.
- A candidate resume belongs to a Service Client but can target a separate Hiring Company.
- An application tracks a candidate's progress for a client and hiring requirement.

The main lifecycle is:

```text
Recruiter assignment
		-> Resume upload and metadata parsing
		-> Candidate becomes visible to the correct client
		-> Application submission
		-> Interview email analysis
		-> Human confirmation
		-> Pipeline and timeline update
		-> Client notification/chat update
		-> Offer, joining, closure, or archive
```

## 2. Product Features

### 2.1 Authentication and Workspace Access

- Login with email and password.
- Passwords are stored as bcrypt hashes.
- Access and refresh JWTs are issued as HTTP-only cookies.
- The frontend also supports a Bearer access token fallback for API requests.
- Access tokens are short-lived; refresh tokens live longer and are restricted to auth endpoints.
- Login records a `login` activity event and starts dashboard pre-warming.
- `/api/auth/bootstrap` returns the current user, role-specific dashboard data, notifications, and unread chat count in one request.
- Logout removes both auth cookies.
- Inactive users cannot authenticate even if their token is otherwise valid.

### 2.2 Service Client Management

Administrators manage the staffing customers represented in the system.

- Create, edit, activate, deactivate, archive, and safely delete clients.
- Assign one or more recruiters to a client.
- Store contact person, email, phone, logo, status, and lifecycle timestamps.
- Filter clients by `active`, `inactive`, `archived`, or `all`.
- Deactivation preserves historical data, blocks the client login, and makes the client's chat read-only.
- Archiving hides a client from default active views while preserving resumes, applications, reports, and history.
- Safe deletion is Super Admin only and fails when historical resumes, applications, or chats would be orphaned.

### 2.3 Recruiter and User Management

- Super Admin and Sub-Admin can create and manage users within their scope.
- Users have a role, active status, account status, optional phone, and optional client association.
- Recruiter-to-client membership is represented by `employee_clients`.
- Assignments can be active/inactive, primary/non-primary, timestamped, and attributed to the assigning administrator.
- Removing a recruiter from a client deactivates the assignment rather than deleting historical work.
- Super Admin manages Sub-Admins; Sub-Admins do not receive global visibility.

### 2.4 Resume and Candidate Management

Recruiters use Candidate Studio to ingest and manage candidate files.

- Upload one or many PDF resumes in a batch.
- Select the Service Client and optionally a requirement before upload.
- Parse standard filenames into metadata. Example:

	```text
	TCS_JavaDeveloper_RES101.pdf
	Company: TCS
	Role: Java Developer
	Resume tag: RES101
	```

- Review and correct metadata before committing files that need manual review.
- Check duplicates before a batch is committed.
- Store files in Google Drive through the Google Apps Script integration when configured.
- Fall back to local `backend/uploads/` storage when Drive is unavailable.
- Preview PDFs inline with `application/pdf` and download them as attachments.
- Search and paginate by keyword, Service Client, requirement, Hiring Company, role, candidate name, resume tag, and upload date.
- Update resume metadata or move a resume between clients according to permission scope.
- Delete a resume from both the database and configured file storage according to permission scope.

### 2.5 Requirements and Job Openings

Requirements describe the work a recruiter is expected to fill for a Service Client.

- Create, view, update, complete, and manage job openings.
- Store job title, designation/code, URL, priority, notes, creator, and completion metadata.
- A requirement can be assigned to all eligible recruiters or one recruiter.
- Requirements are filtered by client and user scope.
- A requirement may be attached to resume uploads and applications.

### 2.6 Applications and Candidate Pipeline

Applications connect a candidate to a Service Client, recruiter, requirement, and hiring process.

- Create an application directly from the candidate bank.
- List applications with client, requirement, employee, status, search, and pagination filters.
- View pipeline statistics grouped by stage.
- Update application status and recruiter/client notes.
- Keep `current_round`, `interview_date`, confidence, AI-processed state, and last email snippet.
- Close an application while preserving its history.
- Archive an application while preserving its history.
- Super Admin alone can permanently delete an application and its related events/email-intake records.
- Timeline events preserve the chronological record of submissions, email intake, interview changes, notes, and closure/archive actions.

### 2.7 AI Interview Intake

The AI inbox turns unstructured interview communications into reviewable application updates using Groq LLaMA.

Supported inputs:

- Pasted email text.
- `.eml` files.
- Text/PDF inputs supported by the file analyzer.
- Image screenshots through OCR when the configured extraction path supports it.

The implemented default flow has two phases:

1. **Analyze / preview**: classify and extract data without writing to the database or posting to chat.
2. **Confirm / save**: persist the reviewed result, update the application, create an event, and post the client-facing chat update.

The analyzer extracts or proposes:

- Candidate name.
- Hiring Company.
- Role.
- Interview status.
- Round name.
- Interview date/time.
- Confidence.
- Service Client.
- Whether the message is related to recruitment.
- Whether it is a new application, follow-up, duplicate, or unknown update.

Unrelated marketing, newsletters, billing, OTPs, spam, and general meeting messages are classified as `not_related` and should not become pipeline records.

#### Smart Resume Linking

When an AI event is confirmed, matching is attempted within the selected Service Client only:

1. Exact resume ID/tag, for example `RES101`.
2. Candidate name plus Hiring Company.
3. Candidate name plus role.
4. No match: retain a pipeline record with a nullable `resume_id` so the event is not silently lost.

The user can edit low-confidence extraction before confirming it.

### 2.8 Targets and Quotas

Targets define a recruiter's expected daily application output for a specific Service Client.

- Admin and Sub-Admin create or update targets.
- Targets belong to an employee/client pair and have an effective date and lifecycle status.
- Targets can be paused, resumed, or ended.
- Deletion is permitted only before the target becomes effective.
- Recruiters see their own target progress; administrators can inspect scoped employees.
- The dashboard recalculates upload, submission, and target metrics using the active filters.

The progress rules are:

$$
	ext{Completion \%} = \left(\frac{\text{Applications Submitted}}{\text{Daily Target}}\right) \times 100
$$

$$
	ext{Remaining} = \max(\text{Daily Target} - \text{Applications Submitted}, 0)
$$

Progress can exceed 100%. The intended visual thresholds are red for 0-50%, orange for 51-99%, and green for 100% or higher.

### 2.9 Dashboards and Telemetry

The bootstrap/dashboard services provide role-specific views.

**Admin and Sub-Admin dashboard**

- Global or scoped client and recruiter metrics.
- Date-range filtering.
- Resume totals and today's uploads.
- Application totals and today's submissions.
- Requirement counts.
- Target totals and completion.
- Attendance summary.
- Team/client performance charts.

**Recruiter dashboard**

- Personal upload and application counts.
- Daily target and remaining work.
- Progress ring that supports over-achievement.
- Assigned client and requirement context.
- Today's attendance status and live session timer.

**Service Client dashboard**

- Its candidate and application counts.
- Interview-stage summaries.
- Hiring Company breakdown.
- Chronological candidate activity.
- Recruiter communication entry point.

The backend also has query/response profiling middleware and cache invalidation for dashboard, notification, and chat mutations.

### 2.10 Attendance

- Recruiters check in once for the current workday.
- Recruiters check out to finish the active session.
- The current status includes check-in, check-out, total hours, and active state.
- The frontend calculates and displays live elapsed time while a session is active.
- Super Admin can view the live attendance summary for today.
- Attendance is tied to the employee and work date.

### 2.11 Client Chat

Chat uses one room per Service Client.

- Recruiters and client users can access rooms only when they are entitled to that client.
- Administrators can oversee rooms according to their management scope.
- Send text messages and share resumes.
- Upload/share attachment references where supported by the chat UI.
- Receive new messages through WebSockets.
- Show typing indicators, read receipts, unread counts, and notifications.
- Mark a room read up to a selected message or mark all messages read.
- Lock/unlock rooms into read-only mode.
- Archive rooms and export chat transcripts.
- Delete messages according to service authorization.
- A deactivated client is read-only; history remains available to authorized internal users.

### 2.12 Notifications

- List the current user's notifications with unread count.
- Mark individual notifications read.
- Notifications are generated for relevant operational events such as application updates, targets, and chat activity.
- The layout shows notification and chat unread badges.

### 2.13 Reports and Exports

- Admin/Sub-Admin Excel export with client and recruiter breakdowns.
- CSV exports for operational data such as clients, employees, and targets.
- Branded recruitment summary PDF output where supported by the report service.
- Report queries respect the caller's management scope.

## 3. Role Rules

| Capability | Super Admin | Sub-Admin | Recruiter | Service Client |
|---|---:|---:|---:|---:|
| View global data | Yes | No | No | No |
| View assigned client data | Yes | Yes | Yes | Own client only |
| Create clients | Yes | Yes, scoped/assigned | No | No |
| Assign recruiters | Yes | Yes, scoped | No | No |
| Create/manage Sub-Admins | Yes | No | No | No |
| Upload resumes | No | No | Yes | No |
| Search visible resumes | Yes | Scoped | Assigned clients | Own client |
| Create applications | Yes, via authorized scope | Scoped | Assigned scope | Read-oriented portal |
| Process AI intake | Yes, via authorized scope | Scoped | Yes | No |
| Set targets | Yes | Yes, scoped | No | No |
| View own target progress | Yes | Yes | Yes | Read-only visibility where exposed |
| Manage attendance | Summary | Dashboard scope where exposed | Check in/out | No |
| Manage clients | Full | Scoped | No | No |
| Permanently delete applications | Yes | No | No | No |
| Permanently delete clients | Yes, safe-delete only | No | No | No |
| Access client chat | Oversight | Scoped oversight | Assigned clients | Own room |

The backend is authoritative for this matrix. Frontend route guards improve the experience but are not security boundaries.

## 4. Backend Module Map

All API routes are registered in `backend/app/main.py`.

| Module | Route prefix | Responsibility |
|---|---|---|
| `auth` | `/api/auth` | Login, refresh, logout, current user, bootstrap |
| `users` | `/api` | User/recruiter CRUD, role and assignment administration |
| `clients` | `/api/clients` | Client lifecycle and recruiter assignments |
| `requirements` | `/api/requirements` | Job openings and recruiter work requirements |
| `resumes` | `/api/resumes` | Candidate search, upload, duplicate checks, file delivery |
| `applications` | `/api/applications` | Applications, pipeline, status, notes, timeline |
| `ai` | `/api/ai` | AI email analysis, confirmation, inbox/history |
| `targets` | `/api/targets` | Daily targets and progress |
| `dashboard` | `/api/dashboard` | Role-specific metrics and dashboard telemetry |
| `reports` | `/api/reports` | Excel, CSV, and PDF exports |
| `attendance` | `/api/attendance` | Check-in, check-out, attendance summaries |
| `notifications` | `/api/notifications` | Notification feed and read state |
| `activity_logs` | `/api/activity-logs` | Audit and compliance history |
| `chat` | `/api/chat` | Rooms, messages, read state, sharing, exports |
| `chat.websocket` | WebSocket route | Real-time room events |

Each module generally contains:

- `models.py`: SQLAlchemy persistence model.
- `schemas.py`: Pydantic request/response contract.
- `service.py`: business rules, queries, and mutations.
- `router.py`: HTTP boundary and dependency wiring.

Shared infrastructure lives under `backend/app/core`:

- `config.py`: environment-backed settings.
- `database.py`: async SQLAlchemy engine, sessions, and base model.
- `dependencies.py`: current-user authentication and role checks.
- `security.py`: bcrypt and JWT operations.
- `cache.py`: short-lived/cache invalidation helpers.
- `profiler.py`: request/query telemetry.

External integrations live under `backend/app/services`:

- `google_drive.py`: Google Drive/App Script storage with local fallback.
- `groq_service.py`: Groq classification and extraction.
- `email_parser.py`: email/file text extraction support.

## 5. Frontend Module Map

The React application is composed in `frontend/src/app/App.jsx` and uses lazy-loaded routes.

| UI route | Feature module | Purpose |
|---|---|---|
| `/login` | `features/auth` | Login and authenticated session context |
| `/dashboard` | `features/dashboard` | Role-specific dashboard |
| `/upload` | `features/resumes` | Recruiter-only resume ingestion |
| `/candidates` | `features/resumes` | Candidate bank, search, preview, edit |
| `/applications`, `/ai-inbox` | `features/applications` | Pipeline and AI response inbox |
| `/chats` | `features/chat` | Client rooms, messages, sharing, real-time events |
| `/requirements` | `features/requirements` | Requirements/job openings |
| `/clients` | `features/clients` | Client lifecycle and assignments |
| `/sub-admins` | `features/subadmins` | Super Admin-only Sub-Admin management |
| `/recruiters` | `features/dashboard` | Recruiter management and target assignment |
| `/targets` | `features/dashboard` | Target configuration and history |
| `/reports` | `features/reports` | Export center |
| `/notifications` | `features/notifications` | Notification history and read state |
| `/performance`, `/admin/performance` | `features/admin` | Admin/Sub-Admin performance dashboard |

Shared frontend infrastructure:

- `components/layout`: sidebar, top bar, page shell, and global badges.
- `components/ui`: dropzone, tables, dialogs, progress rings, notifications, loaders, and toasts.
- `services/api.js`: Axios client, credentials, and auth response handling.
- `styles/index.css`: global design tokens and styling.
- `utils/cn.js`: class-name composition helper.

`ProtectedRoute` checks whether a user is logged in and whether their role is allowed for a route. Unauthorized users are redirected to `/dashboard`; unauthenticated users are redirected to `/login`.

## 6. Database Ownership

| Table/entity | Meaning |
|---|---|
| `users` | Accounts, roles, active state, client association |
| `clients` | Service Clients and lifecycle state |
| `employee_clients` | Recruiter/client assignments |
| `sub_admin_assignments` | Sub-Admin management scope |
| `resumes` | Candidate files and parsed metadata |
| `requirements` | Client job openings and assignment rules |
| `applications` | Candidate pipeline records |
| `application_events` | Application timeline/audit events |
| `email_intakes` | AI/email processing history tied to applications |
| `targets` | Employee/client daily goals |
| `attendance` | Daily employee sessions |
| `chat_rooms` | One room per Service Client |
| `chat_messages` | Messages and attachments |
| `chat_reads` | Per-user read cursor/state |
| `notifications` | In-app alerts and read state |
| `activity_logs` | Security and operational audit trail |

The application imports all models at startup so SQLAlchemy and Alembic know the complete schema. SQLite startup includes compatibility migrations for older local databases; PostgreSQL startup ensures the schema exists and applies selected compatibility columns.

## 7. Pin-to-Pin Workflows

### 7.1 Recruiter Uploads a Resume

1. Recruiter logs in and receives HTTP-only JWT cookies.
2. Frontend loads `/api/auth/bootstrap` for profile, dashboard, notifications, and unread chat state.
3. Frontend allows `/upload` only for role `employee`.
4. Recruiter selects a Service Client, optional requirement, and PDF files.
5. Backend checks the authenticated role again. Non-recruiters receive `403`.
6. Filename parser proposes candidate name, Hiring Company, role, and resume tag.
7. Duplicate check compares the proposed batch with existing client-scoped records.
8. Recruiter removes duplicates and confirms any manual metadata.
9. Storage writes to Google Drive/App Script or local fallback.
10. Resume rows are committed with uploader, client, filename, parsed metadata, and date.
11. Dashboard/cache invalidation causes counts and client views to refresh.

### 7.2 Recruiter Submits a Candidate

1. Recruiter searches the candidate bank within their allowed clients.
2. Recruiter selects a candidate, client, and optional requirement.
3. Backend verifies that the recruiter can access the resume/client.
4. An application is created with status `Submitted`, recruiter, client, and submission date.
5. Application metrics, target progress, activity timeline, notifications, and client views reflect the submission.

### 7.3 Recruiter Processes an Interview Email

1. Recruiter pastes email text or uploads a supported file/screenshot.
2. `/api/ai/analyze-email` or `/api/ai/analyze-file` extracts and classifies content.
3. The preview phase does not persist data or send chat messages.
4. If unrelated, the UI warns the recruiter and stops.
5. If related, the UI shows candidate, company, role, status, round, date, confidence, and match information.
6. Recruiter edits incorrect fields if needed.
7. `/api/ai/confirm-save` receives the verified payload.
8. Service-scoped smart matching tries tag, name/company, then name/role.
9. Existing application is updated or a new application/pipeline record is created.
10. Raw snippet, AI confidence, source type, and processed state are stored.
11. An `application_event` and activity record are written.
12. The client chat room receives an automatic update and relevant notifications are generated.

### 7.4 Client Views Progress

1. Client authenticates as a user linked to exactly one Service Client.
2. Every candidate/application/chat query is restricted to that client.
3. Client sees assigned resumes, application stages, interview updates, and activity timeline.
4. Client can communicate in its room and view shared resumes.
5. If deactivated, the client cannot log in and its room becomes read-only, while historical records remain.

### 7.5 Administrator Sets a Target

1. Admin/Sub-Admin selects a recruiter and Service Client within their management scope.
2. Target value and effective date are submitted to `/api/targets`.
3. Service checks scope and writes or updates the employee/client target.
4. Dashboard aggregates active targets for the selected client/employee/date range.
5. Submitted applications increase completion; remaining work never falls below zero.
6. Target may later be paused, resumed, or ended without deleting its history.

## 8. Security and Data-Isolation Rules

- Authentication is required for all business APIs.
- Backend authorization is based on the database user, not only a frontend role value.
- The access token identifies both user ID and role, but the backend reloads the active user before granting access.
- Client, recruiter, resume, application, target, report, and chat queries must remain inside the caller's allowed scope.
- Resume matching is explicitly restricted by `client_id` to avoid cross-client candidate leakage.
- PDF preview/download first authorizes access, then streams bytes with the correct content disposition.
- ORM queries use SQLAlchemy parameters rather than string-built SQL for normal application operations.
- Upload endpoints validate the intended file type and only employees can bulk-upload resumes.
- Client deactivation is reversible; archive is historical hiding; safe deletion is intentionally stricter.
- Activity logs preserve security-sensitive actions such as login, application closure/archive/deletion, and client lifecycle mutations.
- CORS allows the configured frontend plus local development origins and credentials are enabled for cookies.
- Production should use HTTPS, `secure=True` cookies, a strong `JWT_SECRET_KEY`, non-default admin credentials, and restricted external integration URLs.

## 9. API Groups at a Glance

| Group | Important operations |
|---|---|
| Auth | `POST /login`, `POST /refresh`, `POST /logout`, `GET /me`, `GET /bootstrap` |
| Resumes | `GET /resumes`, `POST /resumes/upload`, `POST /resumes/check-duplicates`, `GET /resumes/{id}/preview`, `GET /resumes/{id}/download` |
| Applications | `GET/POST /applications`, `GET /applications/{id}/timeline`, `POST /applications/{id}/close`, `POST /applications/{id}/archive` |
| AI | `POST /ai/analyze-email`, `POST /ai/analyze-file`, `POST /ai/confirm-save`, `GET /ai/inbox`, `GET /ai/history` |
| Clients | `GET/POST /clients`, `PUT/PATCH /clients/{id}`, activate/deactivate/archive/delete, assign employees |
| Targets | `GET/POST /targets`, progress, pause, resume, end, delete |
| Attendance | status, check-in, check-out, admin summary |
| Chat | rooms, paginated messages, send, share resume, read, lock/unlock, archive, export, unread count |
| Reports | Excel, CSV, and PDF export endpoints |

The health check is `GET /api/health` and returns the service health status.

## 10. Runtime and Deployment

### Backend

- Python 3.11+.
- FastAPI with Uvicorn.
- Async SQLAlchemy 2.0.
- SQLite is supported for local development.
- PostgreSQL/Neon is supported for production.
- Run from `backend` with `uvicorn app.main:app --reload --port 8000`.
- Interactive API documentation is available at `/docs`.

### Frontend

- React 18 with Vite.
- React Router for protected workspace routes.
- Tailwind CSS styling.
- Run from `frontend` with `npm install` and `npm run dev`.
- The local frontend normally runs at `http://localhost:5173`.

### Important environment values

- `USE_SQLITE` and `DATABASE_URL_OVERRIDE` select local database behavior.
- `JWT_SECRET_KEY`, `JWT_ALGORITHM`, access expiry, and refresh expiry control authentication.
- `GROQ_API_KEY` enables AI intake.
- `GOOGLE_APPS_SCRIPT_URL` enables cloud resume storage.
- `FRONTEND_URL` controls the configured frontend origin for CORS.
- Admin identity and password should be supplied through environment settings and changed from any initial development values.

## 11. Current Boundaries and Caveats

- The frontend has aliases `/applications` and `/ai-inbox` for the same AI response inbox page.
- Frontend route restrictions and backend role checks should remain aligned; only backend checks provide real protection.
- The README describes broad client/admin chat oversight, while room access is ultimately decided by the chat service's scoped authorization.
- Local SQLite compatibility migrations exist for evolving development databases; production schema changes should be managed through Alembic migrations.
- Google Drive is optional because the storage service has a local fallback.
- Direct AI legacy endpoints (`/api/ai/process-email` and `/api/ai/upload-email`) still exist for backward compatibility and automatically confirm after analysis. New UI flows should use preview then explicit confirmation.
- Roadmap items such as direct Gmail/Outlook OAuth, calendar synchronization, scanned-resume OCR, and custom KPI builders are future capabilities unless separately implemented.

## 12. Source of Truth

When behavior in this guide and a live implementation disagree, inspect these ownership points first:

1. `backend/app/main.py` for registered routers and startup behavior.
2. `backend/app/core/dependencies.py` for authentication and role enforcement.
3. The relevant module's `router.py` for the API contract.
4. The relevant module's `service.py` for actual business rules and scoping.
5. `frontend/src/app/App.jsx` for visible routes and frontend role gates.
6. `frontend/src/services/api.js` for client transport and session behavior.

The most important architectural rule is that the **service layer owns scope and business decisions**, while routers and frontend components provide the transport and user interface around those decisions.
