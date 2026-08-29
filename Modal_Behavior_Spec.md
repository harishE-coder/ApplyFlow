# ApplyFlow ATS — Complete Modal & Drawer Behavior Specification

> **Specification Version**: 1.2.0  
> **Dialog Standards**: Framer Motion entrance animations, full focus trapping, `Escape` key dismissal, non-scrolling document body (`overflow: hidden`), and contextual validation

---

## 1. Modal Registry & Overview

| Modal Name | Trigger Point | Allowed Roles | Backend Endpoint |
| :--- | :--- | :--- | :--- |
| **Manual Upload Review Modal** | Upload Page (When file has low confidence / mismatch) | `employee` | `POST /api/resumes/confirm-manual` |
| **Create/Edit Client Modal** | Service Clients Page (`/clients`) | `admin`, `sub_admin` | `POST /api/clients`, `PUT /api/clients/{id}` |
| **Assign Recruiters Modal** | Service Clients Page (`/clients`) | `admin`, `sub_admin` | `POST /api/clients/{id}/employees` |
| **Create/Edit Requirement Modal** | Requirements Page (`/requirements`) | `admin`, `sub_admin`, `employee` | `POST /api/requirements`, `PUT /api/requirements/{id}` |
| **Set Daily Target Modal** | Targets Page (`/targets`) | `admin`, `sub_admin` | `POST /api/targets` |
| **AI Extraction Confirmation Card** | AI Response Inbox (`/applications`) | `admin`, `sub_admin`, `employee` | `POST /api/ai/confirm-save` |
| **Resume Inline Preview Drawer** | Candidate Studio / Chat / Applications | All Roles (Scoped) | `GET /api/resumes/{id}/preview` |
| **Resume Chat Share Modal** | Client Chat Window (`/chats`) | `admin`, `sub_admin`, `employee` | `POST /api/chat/rooms/{id}/share-resume` |
| **Command Palette (`⌘K`)** | Global Application Frame | All Roles | `GET /api/auth/bootstrap`, `GET /api/resumes` |
| **Delete Confirmation Modal** | Candidates, Requirements, Clients, Targets | Role-Specific | `DELETE /api/{module}/{id}` |

---

## 2. Detailed Modal Specifications

### 2.1 Manual Upload Review Modal
- **Purpose**: Allows recruiters to review and edit candidate metadata before committing files that failed automatic filename validation.
- **Form Controls**:
  - `Candidate Name Input`: Required text.
  - `Service Client Dropdown`: Pre-populated with recruiter's assigned clients.
  - `Target Company Input`: e.g. *TCS*, *Amazon*.
  - `Role Title Input`: e.g. *Senior Java Developer*.
  - `Resume Tag Input`: e.g. *RES101*.
  - `Resume Date`: `YYYY-MM-DD`.
- **Validation**: Cannot submit if Service Client or Candidate Name is empty.
- **Success Behavior**: Calls `POST /api/resumes/confirm-manual`, closes modal, triggers confetti, updates recruiter dashboard metrics.

---

### 2.2 Create / Edit Client Modal
- **Purpose**: Provision or update a Service Client company.
- **Form Controls**:
  - `Company Name`: Required, unique string.
  - `Contact Person`: Full name of customer liaison.
  - `Billing / Work Email`: Valid email address.
  - `Phone Number`: Formatted telephone string.
  - `Logo URL`: Optional image link.
- **Validation**: Checks for duplicate client names inline.
- **Success Behavior**: Calls `POST /api/clients`, invalidates client cache, adds client to dropdowns.

---

### 2.3 Assign Recruiters Modal
- **Purpose**: Assigns talent specialists to a Service Client.
- **Form Controls**:
  - `Recruiter Checkbox List`: Shows recruiter name, email, and current client load.
  - `Primary Lead Radio Toggle`: Selects primary account lead.
- **Success Behavior**: Calls `POST /api/clients/{id}/employees`, triggers in-app notification to newly assigned recruiters, updates chat room access permissions.

---

### 2.4 Create / Edit Requirement Modal
- **Purpose**: Creates a client hiring requisition / job opening.
- **Form Controls**:
  - `Service Client Dropdown`: Scoped to user's permissions.
  - `Target Company`: e.g. *Infosys*.
  - `Role Title`: e.g. *Fullstack React Engineer*.
  - `Role Code`: Required identifier (e.g. *INF-REACT-01*).
  - `Careers URL`: Optional link to employer job posting.
  - `Priority`: Dropdown (`High`, `Medium`, `Low`).
  - `Assignment Mode`: Toggle between `All Assigned Recruiters` and `Specific Recruiter`.
- **Success Behavior**: Calls `POST /api/requirements`, invalidates dashboard cache, shows success toast.

---

### 2.5 Set Daily Target Modal
- **Purpose**: Configures daily candidate submission goals.
- **Form Controls**:
  - `Recruiter Dropdown`: Selected recruiter.
  - `Service Client Dropdown`: Target customer account.
  - `Daily Target Number`: Integer (1 to 100).
  - `Effective Date`: Date picker (`YYYY-MM-DD`).
- **Success Behavior**: Calls `POST /api/targets`, recalculates quota donut ring on recruiter dashboard.

---

### 2.6 Resume Chat Share Modal
- **Purpose**: Allows recruiters to attach candidate profiles directly into a client conversation.
- **Form Controls**:
  - `Candidate Search Bar`: Filters candidate bank by name, role, or resume tag.
  - `Resume Selection Radio List`: Displays candidate card preview.
- **Success Behavior**: Calls `POST /api/chat/rooms/{id}/share-resume`, attaches interactive candidate card into WebSocket message stream, and auto-scrolls chat to bottom.





# ApplyFlow ATS — Complete Page Behavior Specification

> **Specification Version**: 1.2.0  
> **Target Audience**: Frontend Engineers, QA Automation Engineers, Product Designers  
> **Routing Architecture**: React Router v7 with dynamic `React.lazy()` chunking and `ProtectedRoute` role guards

---

## 1. Page Catalog & Route Hierarchy

```
/login                          -> LoginPage (Public)
/dashboard                      -> DashboardPage (Role-Adaptive: Admin, Recruiter, Client)
/upload                         -> UploadPage (Employee / Recruiter Exclusive)
/candidates                     -> ResumesPage (Candidate Studio Master-Detail)
/applications                   -> AIResponseInboxPage (AI Email Intake & Pipeline)
/ai-inbox                       -> AIResponseInboxPage (Alias Route)
/chats                          -> ChatPage (Real-Time WebSocket Client Rooms)
/requirements                   -> RequirementsPage (Job Openings & Requisitions)
/clients                        -> ClientsPage (Service Client Lifecycle & Assignments)
/sub-admins                     -> SubAdminsPage (Super Admin Exclusive Delegation)
/recruiters                     -> RecruitersPage (Recruiter Management & Quotas)
/targets                        -> TargetsPage (Daily Submission Targets & History)
/reports                        -> ReportsPage (Multi-Format Export Center)
/notifications                  -> NotificationsPage (Operational Alerts Feed)
/performance                    -> PerformanceDashboardPage (System & SQL Profiler)
```

---

## 2. Exhaustive Page Specifications

### 2.1 Login Portal (`/login`)
- **Route**: `/login`
- **Allowed Roles**: Public (Unauthenticated users only). Authenticated users redirected to `/dashboard`.
- **Layout Architecture**: Split-screen (42% Left Brand Panel / 58% Right Login Form Card).
- **Form Controls & Validation**:
  - `Email Input`: Must be non-empty, auto-trimmed, lowercase, and matching RFC 5322 regex.
  - `Password Input`: Minimum 6 characters. Visibility toggle icon (`Eye` / `EyeOff`).
  - `Submit Button`: Triggers `POST /api/auth/login`. Disabled while loading.
- **Error Handling**:
  - HTTP 401: Displays inline shake animation and error toast: `"Invalid email or password"`.
  - Network Error: Displays `"Server unreachable. Check connection."`.
- **Success Flow**:
  - Stores user profile in `AuthContext`.
  - Sets HTTP-only cookies `access_token` and `refresh_token`.
  - Redirects user to `/dashboard`.

---

### 2.2 Dashboard Page (`/dashboard`)
- **Route**: `/dashboard`
- **Allowed Roles**: `admin`, `sub_admin`, `employee`, `client`.
- **Behavior by Role**:
  - **Super Admin (`admin`)**: Renders `AdminDashboard.jsx`. Loads global company metrics, 4 cascading filters, recruiter leaderboard table, and 4 telemetry charts.
  - **Sub-Admin (`sub_admin`)**: Renders `AdminDashboard.jsx` with metrics and filters strictly scoped to assigned clients and recruiters.
  - **Recruiter (`employee`)**: Renders `EmployeeDashboard.jsx`. Displays personal KPI strip, batch resume dropzone, live daily target donut, shift timer ticker, and personal activity stream.
  - **Service Client (`client`)**: Renders `ClientDashboard.jsx`. Displays candidate count, active pipeline stages, hiring company breakdown, and activity timeline.

---

### 2.3 Batch Upload Studio (`/upload`)
- **Route**: `/upload`
- **Allowed Roles**: `employee` (Recruiters only). Super Admins and Clients attempting to access are redirected to `/dashboard` with an error toast.
- **Form Controls & Workflow**:
  1. `Service Client Dropdown`: Loaded from `GET /api/clients`. Pre-selects first assigned client.
  2. `Resume Date Picker`: Defaults to current local date (`YYYY-MM-DD`).
  3. `Optional Requirement Dropdown`: Filters active jobs for the selected client.
  4. `Batch Dropzone`: Handles multi-PDF file drop (1 to 100+ files).
  5. `Ingestion Queue Table`: Parses filename into 4 editable columns (Service Client, Target Company, Role, Resume Identifier).
  6. `Validation & Duplicate Detection`:
     - Calls client-side tokenizer: verifies first segment matches selected client.
     - Automatically calls `POST /api/resumes/check-duplicates` to flag duplicates in Amber.
  7. `Commit Action`: Submits files via `POST /api/resumes/upload`. On success, triggers confetti celebration burst and clears the queue.

---

### 2.4 Candidate Studio & Candidate Bank (`/candidates`)
- **Route**: `/candidates`
- **Allowed Roles**: All roles (Scoped).
- **Layout Architecture**: Master-Detail Split Canvas (40% Left Candidate Feed / 60% Right Secure PDF Streamer).
- **Search & Filter Controls**:
  - Global search input (Debounced at 300ms) matching candidate name, company, role, or resume tag.
  - Service Client dropdown filter.
  - Target Hiring Company dropdown filter (TCS, Infosys, Amazon, etc.).
  - Date range filter (Today, Yesterday, Week, Month, Custom).
- **Master Feed Behavior**:
  - Lists 20 candidates per page.
  - Clicking any candidate row highlights the card and loads the candidate's PDF in the right pane.
- **Detail Viewer Behavior**:
  - Streams binary PDF via `GET /api/resumes/{id}/preview` into an embedded PDF canvas.
  - Action buttons: Download PDF, Open AI Linking, Share to Client Chat.
  - Client Notes pane with `Share with Client` toggle.

---

### 2.5 Groq AI Response Inbox & Applications (`/applications` and `/ai-inbox`)
- **Route**: `/applications` (and `/ai-inbox`)
- **Allowed Roles**: All roles (Scoped).
- **Sub-Views**:
  - `Intake Studio Tab`: Multi-channel ingestion engine (Paste Raw Text, Upload `.eml`, Upload PDF, Screenshot OCR).
  - `Pipeline Events Tab`: Chronological candidate progression feed with event badges.
- **Groq AI Analysis Flow**:
  1. User enters raw interview email and clicks "Analyze with Groq LLaMA 3.3".
  2. Backend executes Phase 1 preview extraction (`POST /api/ai/analyze-email`).
  3. If classified as `not_related`, displays a warning banner and halts.
  4. If classified as positive interview mail, renders the **AI Extraction Card**:
     - Pre-fills Candidate, Company, Role, Status, Round, Date.
     - Displays 4-Tier Smart Resume Linking result with priority badge.
     - User reviews or edits fields inline.
  5. User clicks "Confirm & Advance Pipeline".
  6. Backend executes Phase 2 save (`POST /api/ai/confirm-save`), updating database, event log, and client chat.

---

### 2.6 Real-Time Role-Based Chat (`/chats`)
- **Route**: `/chats`
- **Allowed Roles**: All roles (Scoped).
- **Layout Architecture**: Split-pane (30% Left Room List / 70% Right Conversation Canvas).
- **Room Selection & Presence**:
  - Lists one room per Service Client. Displays unread message badge count.
  - Selecting a room loads recent message history (`GET /api/chat/rooms/{id}/messages`) and establishes WebSocket connection (`WS /api/chat/ws/{id}`).
- **Messaging Controls**:
  - Text input with Shift+Enter for multiline and Enter to send.
  - "Share Resume" button: Opens modal allowing recruiter to pick candidate resume to attach inline.
  - "Typing..." indicator appears when remote participant types.
  - Marking messages as read emits read receipt via WebSocket.

---

### 2.7 Job Openings & Requirements Board (`/requirements`)
- **Route**: `/requirements`
- **Allowed Roles**: All roles (Scoped).
- **Tabs**: Active Requisitions (`active`), Completed History (`done`), Archived (`archived`).
- **Interactive Actions**:
  - "Create Job Opening" button (Admin, Sub-Admin, Recruiter).
  - "Mark Done" action: Prompts completion confirmation, records timestamp and user.
  - "Reopen" action: Moves completed requisition back to active tab.

---

### 2.8 Service Client Management (`/clients`)
- **Route**: `/clients`
- **Allowed Roles**: `admin`, `sub_admin`, `employee` (Recruiters can view assigned; Admins can manage).
- **Features & Actions**:
  - Filter by Active, Inactive, Archived, All.
  - "Add Service Client" Button (Admins only).
  - "Assign Recruiters" Modal: Assigns lead and member recruiters.
  - Status Toggle: Deactivating a client marks account inactive and locks client chat into read-only mode.

---

### 2.9 Sub-Admin Delegation Center (`/sub-admins`)
- **Route**: `/sub-admins`
- **Allowed Roles**: `admin` (Super Admin exclusive).
- **Features**:
  - Lists all Sub-Admin users.
  - "Assign Clients & Teams" modal: Multi-select checkboxes mapping Service Clients and Recruiters to each Sub-Admin.

---

### 2.10 Targets & Quotas Hub (`/targets`)
- **Route**: `/targets`
- **Allowed Roles**: `admin`, `sub_admin`, `employee` (Recruiters see own; Admins manage).
- **Actions**:
  - "Set Daily Target" modal.
  - Inline actions: "Pause", "Resume", "End", "Delete" (Allowed only before target effective date).

---

### 2.11 Multi-Format Reports Center (`/reports`)
- **Route**: `/reports`
- **Allowed Roles**: All roles (Scoped).
- **Exports**:
  - "Download Master Excel Report (`.xlsx`)": Triggers download of multi-sheet workbook.
  - "Generate Executive PDF Summary": Generates branded PDF report.
  - CSV Data Exports: Active Clients, Inactive Staff, Completed Targets.

---

### 2.12 In-App Notification Center (`/notifications`)
- **Route**: `/notifications`
- **Allowed Roles**: All roles.
- **Actions**:
  - Click notification row to mark read and navigate to relevant candidate or chat room.
  - "Mark All Read" button.
  - "Clear Notifications Older Than 30 Days" button.

---

### 2.13 Architecture & Performance Dashboard (`/performance` and `/admin/performance`)
- **Route**: `/performance`
- **Allowed Roles**: `admin`, `sub_admin`.
- **Telemetry Display**:
  - In-Memory Cache Stats: Active cached keys, TTL expirations, cache tag invalidations.
  - SQL Profiler Telemetry: Average queries per request, average SQL latency in ms, slow-query log.
