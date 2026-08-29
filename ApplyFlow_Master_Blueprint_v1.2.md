# ApplyFlow — Master Architecture & System Blueprint (v1.2)

> **Document Classification**: Enterprise Architecture & Complete System Specification  
> **Target Audience**: Principal Architects, Lead Software Engineers, Security Engineers, QA Directors, Database Architects, UI/UX Directors  
> **System Version**: ApplyFlow v1.2 Production  
> **Core Stack**: FastAPI (Python 3.11+), SQLAlchemy 2.0 Async, React 18, Vite 6, Tailwind CSS v4, Groq AI LLaMA 3.3 (70B), Google Apps Script Storage Engine, WebSockets

---

# Chapter 1 — Vision & Strategic Purpose

## 1.1 The Fundamental Problem in Recruitment Operations
Modern recruitment agencies, talent consulting firms, and staffing organizations operate under extreme velocity pressures. A single recruiter often manages 30 to 80 candidate submissions daily across multiple customer accounts while coordinating interviews with dozens of hiring companies. 

However, traditional recruitment software creates severe operational bottlenecks:
1. **Generic ATS Platforms Fail Agency Models**: Off-the-shelf Applicant Tracking Systems (e.g., Greenhouse, Lever, Workable) are built for single-company internal HR teams. They assume the organization hiring the candidate is also the entity operating the software. They cannot cleanly distinguish between:
   - The **Service Client** (the customer paying the staffing firm).
   - The **Hiring Company** (the end-employer where the candidate will actually work, e.g., Google, TCS, Amazon).
   - The **Recruiter Assignment** (which talent specialists are authorized to work on which client contracts).
2. **Spreadsheet Chaos & Data Leakage**: In the absence of an agency-tailored operating system, recruitment teams default to Microsoft Excel or Google Sheets. This causes:
   - Zero access control (recruiters can accidentally overwrite or leak candidates across competing clients).
   - Duplicate candidate submissions (submitting the same profile to the same employer twice, causing contractual disputes and reputation damage).
   - Unsearchable file stores (thousands of PDFs dumped into messy desktop folders or shared Google Drives with inconsistent naming).
3. **Interview Tracking Friction**: Interview scheduling updates arrive via unstructured emails (often 100+ emails a day from hiring managers). Manually reading, extracting dates, finding candidate records, advancing pipeline stages, and notifying clients takes 3–4 hours per recruiter per day.

## 1.2 The ApplyFlow Solution
**ApplyFlow** is a purpose-built, high-velocity recruitment workspace and talent operating system designed specifically for recruitment agencies, staffing firms, and Talent Operations teams.

ApplyFlow eliminates agency friction through four core pillars:
- **Strict Multi-Tenant Customer Isolation**: Every resume, application, job opening, and chat message is strictly scoped to a Service Client. Data cannot cross organizational boundaries.
- **Batch Resume Ingestion with Strict Tokenization**: Recruiters can drag and drop 1 to 100+ resumes simultaneously. Standardized filenames (`ServiceClient_Company_Role_ID.pdf`) are tokenized instantly with pre-commit duplicate detection.
- **Groq-Powered AI Email Interview Intake (LLaMA 3.3 70B)**: Unstructured interview invitation emails are parsed in under 800ms. A 4-tier smart matching algorithm identifies the exact candidate and advances the pipeline automatically.
- **Real-Time Agency Telemetry & Quota Engine**: Daily submission quotas, attendance session timers, client communication channels, and multi-sheet Excel/PDF reports operate in real time.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                     APPLYFLOW AGENCY WORKSPACE                                   │
├────────────────────────────────┬────────────────────────────────┬───────────────────────────────┤
│        SERVICE CLIENTS         │        HIRING COMPANIES        │          RECRUITERS           │
│   (Paying Staffing Customers)  │     (End-Client Employers)     │    (Talent Specialists with   │
│   e.g., ABC Staffing           │     e.g., TCS, Infosys, Amazon │     Assigned Client Quotas)   │
└────────────────────────────────┴────────────────────────────────┴───────────────────────────────┘
```

---

# Chapter 2 — Core Business Model

## 2.1 The Critical Distinction: Service Client vs. Hiring Company

The architectural foundation of ApplyFlow rests on the strict separation of **Service Clients** and **Hiring Companies**.

| Dimension | Service Client (`clients` table) | Hiring Company (`company` field) |
| :--- | :--- | :--- |
| **Definition** | The paying customer who contracted our agency for recruitment services. | The end-client organization where the candidate will physically or remotely work. |
| **Examples** | *ABC Staffing*, *Talent Hub Global*, *NextHire Consulting*. | *Google*, *Amazon*, *Tata Consultancy Services (TCS)*, *Infosys*. |
| **Database Entity** | First-class relational entity with primary key UUID, contact information, lifecycle state, and Google Drive folder references. | Normalized metadata string attached to `resumes`, `requirements`, and `applications`. |
| **System Access** | Has dedicated portal logins (`role="client"`). Client users can log in to view candidate pipelines and chat with assigned recruiters. | No system login. Purely a data entity representing the requisition target. |
| **Recruiter Assignment** | Recruiters (`role="employee"`) are formally assigned to Service Clients via `employee_clients`. | Recruiters submit candidates to Hiring Companies *on behalf* of the Service Client. |
| **Lifecycle** | `active`, `inactive` (login blocked, chat read-only), `archived` (hidden from active views), `deleted` (safe-deletion only if zero historical data). | Metadata value, filtered dynamically in search and dashboard dropdowns. |

## 2.2 Entity Relationship & Ownership Hierarchy

```
┌──────────────────────────────────────────────────────────────────────────┐
│                               SUPER ADMIN                                │
│                   (Global Platform & Business Owner)                     │
└─────────────────────┬──────────────────────────────┬─────────────────────┘
                      │                              │
                      ▼                              ▼
┌────────────────────────────────────────┐ ┌──────────────────────────────┐
│               SUB-ADMIN                │ │        SERVICE CLIENT        │
│    (Delegated Scope over Clients)      │ │   (Paying Customer Portal)   │
└─────────────────────┬──────────────────┘ └──────────────┬───────────────┘
                      │                                   │
                      ▼                                   ▼
┌────────────────────────────────────────┐ ┌──────────────────────────────┐
│          EMPLOYEE / RECRUITER          │ │      CLIENT CANDIDATES       │
│  (Assigned to 1..N Service Clients)    │ │   (Scoped to Service Client) │
└─────────────────────┬──────────────────┘ └──────────────┬───────────────┘
                      │                                   │
                      ▼                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          APPLICATION PIPELINE                           │
│     (Candidate Resume + Target Hiring Company + Stage Transitions)      │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# Chapter 3 — Complete Role Architecture

ApplyFlow enforces strict Role-Based Access Control (RBAC) across four user roles:

## 3.1 Super Admin (`admin`)
- **Strategic Purpose**: Complete executive authority over the entire platform, agency operations, staff management, and system configuration.
- **Responsibilities**:
  - Provision, manage, and configure Sub-Admins, Recruiters, and Client Portal accounts.
  - Create and configure Service Clients; assign recruiter teams and leads.
  - Set and adjust daily submission targets per recruiter per client.
  - Monitor global agency telemetry, live attendance, and team velocity.
  - Export executive multi-sheet Excel reports and branded PDFs.
  - Perform safe-deletion of records where permitted.
- **Critical Architectural Restriction**: Super Admins **cannot upload candidate resumes directly** (`/upload` route returns HTTP 403). This preserves recruiter accountability, ensures audit trail integrity, and prevents quota inflation.

## 3.2 Sub-Admin (`sub_admin`)
- **Strategic Purpose**: Delegated operational management over specific client accounts and recruiter pods without global administrative authority.
- **Responsibilities**:
  - Supervise assigned Service Clients and assigned Recruiters defined in `sub_admin_assignments`.
  - Set daily targets for assigned recruiters.
  - View telemetry and analytics strictly scoped to assigned clients.
  - Create job requirements for assigned clients.
  - Oversee client chat rooms within their management boundary.
- **Restrictions**: Cannot view platform-wide totals; cannot access or modify Sub-Admin configurations; cannot upload resumes directly.

## 3.3 Employee / Recruiter (`employee`)
- **Strategic Purpose**: The operational workforce responsible for candidate sourcing, bulk resume ingestion, client delivery, and interview advancement.
- **Responsibilities**:
  - Ingest bulk candidate resumes into assigned Service Clients via Candidate Studio.
  - Submit candidates to open client requisitions.
  - Process interview invitation emails using the Groq AI Inbox.
  - Clock in and out daily via Shift Attendance.
  - Track real-time progress against daily submission quotas.
  - Direct communication with client contacts via Client Chat.
- **Restrictions**: Cannot create or delete clients; cannot view or modify targets; can only view and upload to assigned clients.

## 3.4 Service Client (`client`)
- **Strategic Purpose**: External customer portal for hiring managers and client contacts to review submitted talent, track interview stages, and collaborate with recruiters.
- **Responsibilities**:
  - Review submitted candidate profiles and view zero-leakage PDF resumes inline.
  - Inspect live pipeline stages (Shortlisted, Technical Rounds, Offer, Joining).
  - Communicate directly with assigned agency recruiters via dedicated chat room.
- **Restrictions**: Zero access to internal recruiter targets, internal attendance rosters, or cross-client candidate data; cannot upload or delete resumes; cannot create requirements.

## 3.5 Role Capability Comparison Matrix

| Capability / Action | Super Admin | Sub-Admin | Employee (Recruiter) | Service Client |
| :--- | :---: | :---: | :---: | :---: |
| **Global Telemetry & Dashboards** | Full Global | Scoped to Assigned | Personal Workspace | Customer Portal |
| **Bulk Resume Ingestion (`/upload`)** | ❌ Protected | ❌ Protected | ✅ Exclusive | ❌ Protected |
| **Candidate Search & Split Studio** | Global Bank | Scoped Bank | Assigned Bank | Own Client Only |
| **AI Interview Email Intake** | ✅ Global | ✅ Scoped | ✅ Assigned Scope | ❌ No Access |
| **Set & Edit Daily Targets** | ✅ Full Control | ✅ Scoped Team | ❌ View Only | ❌ No Access |
| **Shift Attendance (Check In/Out)** | Live Roster | Dashboard Scope | ✅ Active Timer | ❌ No Access |
| **Client Lifecycle (Create/Archive)** | ✅ Global | ✅ Scoped | ❌ No Access | ❌ No Access |
| **Sub-Admin Delegation** | ✅ Exclusive | ❌ No Access | ❌ No Access | ❌ No Access |
| **Chat Room Oversight** | All Rooms | Scoped Rooms | Assigned Rooms | Own Client Room |
| **Permanent Delete Applications** | ✅ Admin Only | ❌ Forbidden | ❌ Forbidden | ❌ Forbidden |
| **Multi-Sheet Excel / PDF Export** | ✅ Full Report | ✅ Scoped Report | ✅ Assigned Data | ✅ Client PDF |

---

# Chapter 4 — Navigation & Global Information Architecture

The ApplyFlow user interface is structured around a persistent floating sidebar (`#081226`), a frosted-glass header with global search (`⌘K`), and responsive viewports.

## 4.1 Global Navigation Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            APPLYFLOW NAVIGATION                             │
├───────────────────┬───────────────────────────────┬─────────────────────────┤
│ SECTION           │ ITEM & ROUTE                  │ ROLE VISIBILITY         │
├───────────────────┼───────────────────────────────┼─────────────────────────┤
│ Core Workspace    │ Dashboard (`/dashboard`)      │ All Roles (Adaptive)    │
├───────────────────┼───────────────────────────────┼─────────────────────────┤
│ Recruitment       │ Upload Resumes (`/upload`)    │ Employee Only           │
│                   │ Candidates (`/candidates`)    │ All Roles (Scoped)      │
│                   │ Applications (`/applications`)│ All Roles (Scoped)      │
│                   │ Chats (`/chats`)              │ All Roles (Scoped)      │
│                   │ Job Openings (`/requirements`)│ All Roles (Scoped)      │
├───────────────────┼───────────────────────────────┼─────────────────────────┤
│ Management        │ Service Clients (`/clients`)  │ Admin, Sub-Admin, Emp   │
│                   │ Sub-Admins (`/sub-admins`)    │ Admin Only              │
│                   │ Recruiters (`/recruiters`)    │ Admin, Sub-Admin        │
│                   │ Targets & Goals (`/targets`)  │ Admin, Sub-Admin, Emp   │
├───────────────────┼───────────────────────────────┼─────────────────────────┤
│ Insights          │ Reports & Analytics (`/reports`)│ All Roles (Scoped)    │
│                   │ Notifications (`/notifications`)│ All Roles (Personal)  │
│                   │ Performance (`/performance`)  │ Admin, Sub-Admin        │
└───────────────────┴───────────────────────────────┴─────────────────────────┘
```

---

# Chapter 5 — Every Page Documentation

## 5.1 Authentication Portal (`/login`)
- **Purpose**: Secure credential verification and session bootstrapping.
- **Layout**: 42% Left Branding showcase (dark navy `#081226` with animated radial blue/orange ambient glow) and 58% Right high-precision login card (`#FFFFFF`).
- **Interactive Units**:
  - Work Email Input (`type="email"`, auto-trimmed, validated against RFC 5322).
  - Password Input (`type="password"`, toggleable visibility icon).
  - "Sign In to ApplyFlow" Primary Button with integrated loading spinner.
- **Backend Flow**: `POST /api/auth/login` verifies bcrypt hash, issues HTTP-only `access_token` and `refresh_token` cookies, seeds memory cache, and fires background task `warm_user_dashboard()`.

## 5.2 Recruiter Workspace (`/dashboard` for `employee`)
- **Purpose**: High-velocity daily cockpit for talent specialists.
- **Layout**: 70% Left Column (Ingestion Dropzone, 7-Day Trend Chart, Active Client Jobs, AI Inbox Telemetry) / 30% Right Column (Daily Target Progress Donut, Shift Attendance Session Timer, Personal Activity Stream).
- **Interactive Units**:
  - **KPI Strip**: 4 live cards (Today's Uploads, Applications Submitted, Daily Target Quota, Completion Percentage).
  - **Fast Ingestion Dropzone**: Accepts 1 to 100+ PDFs with pre-parsing and duplicate indicators.
  - **Shift Attendance Box**: Live running session ticker (`HH:MM:SS`) with Check-In/Check-Out action buttons.
  - **Daily Target Ring**: SVG Progress Donut with dynamic color shifts: Red (0–50%), Orange (51–99%), Emerald Green (100%+ with over-achievement badge).

## 5.3 Super Admin Operations Center (`/dashboard` for `admin`)
- **Purpose**: Global command center for cross-client operations and quota enforcement.
- **Interactive Units**:
  - **Cascading Filter Bar**: Service Client selector, Recruiter selector, Global Date preset / DatePicker.
  - **Global Telemetry Cards**: Daily Target total, Submitted total, Agency Completion %, Remaining Applications, Active Recruiters, Sub-Admin count.
  - **Recruiter Leaderboard Table**: Live per-recruiter throughput with colored inline progress bars.
  - **4 Telemetry Charts**: Target vs. Actual Submissions (Grouped Bar), 7-Day Velocity Curve (Spline Area), Client Performance Breakdown (Horizontal Bar), Application Stage Distribution (Donut).

## 5.4 Candidate Studio & Candidate Bank (`/candidates`)
- **Purpose**: High-density talent search and zero-leakage PDF evaluation.
- **Layout**: Master-Detail Split-Screen (40% Left Candidate Feed / 60% Right Secure PDF Streamer).
- **Interactive Units**:
  - Multi-param search bar (Candidate Name, Role, Target Company, Resume Tag `RES101`).
  - Service Client and Target Company dropdown filters.
  - Candidate Card: Displays Candidate Name, Company badge, Role, Resume ID, Upload Timestamp, Application Status.
  - Secure PDF Streamer: Direct binary stream via `GET /api/resumes/{id}/preview` (rendered with zero public URL exposure). Action buttons for PDF Download, AI Link, and Client Chat Share.

## 5.5 Batch Upload Studio (`/upload`)
- **Purpose**: Bulk resume ingestion engine exclusively for Recruiters.
- **Interactive Units**:
  - Service Client selector and optional Requirement selector.
  - Batch Dropzone supporting up to 100+ PDF files.
  - Ingestion Queue Table with inline editable fields (Service Client, Target Company, Role, Resume Identifier).
  - Status Indicators: `ServiceClient Verified` (Green), `ServiceClient Mismatch` (Red), `Duplicate Exists` (Orange).
  - "Commit Verified Resumes" Action Button triggering canvas-confetti on completion.

## 5.6 Groq AI Interview Intake & Application Pipeline (`/applications` and `/ai-inbox`)
- **Purpose**: Automated parsing and transformation of unstructured interview emails into structured candidate progression.
- **Interactive Units**:
  - **Multi-Channel Intake**: 4 tabs (Paste Raw Email, Upload `.eml`, Upload PDF Invite, Upload Screenshot OCR).
  - **Sample Triggers**: 1-click loading of realistic interview invites, round updates, offer letters, and spam emails.
  - **Groq LLaMA 3.3 70B Analyzer**: Extracts Candidate, Company, Role, Status, Round, Interview Date, and Resume Tag.
  - **4-Tier Smart Resume Linking Card**: Displays match confidence, matched resume filename, and priority tier with 1-click manual override.
  - **Confirmation Action**: `POST /api/ai/confirm-save` creates/advances application, creates `application_events`, posts update to Client Chat, and dispatches in-app notifications.

## 5.7 Real-Time Role-Based Chat (`/chats`)
- **Purpose**: Secure customer-recruiter collaboration with inline resume attachments.
- **Interactive Units**:
  - Chat Room Sidebar: One room per Service Client, unread message badges, active presence indicator.
  - Message Stream: Timestamped speech bubbles, sender avatars, read receipts (`✓✓ Read 10:36 AM`).
  - Resume Attachment Card: Interactive candidate card with inline preview and download triggers.
  - Message Input Bar: Text box with emoji support, resume share modal trigger, file attachment slot.
  - WebSocket Synchronization: Real-time broadcast of messages, typing indicators, and read states.

## 5.8 Job Openings & Requirements Board (`/requirements`)
- **Purpose**: Client requisition tracking and recruiter task assignment.
- **Interactive Units**:
  - Status Tabs: Active Requisitions (`active`), Completed History (`done`), Archived (`archived`).
  - Priority Badges: High (`#EF4444`), Medium (`#F97316`), Low (`#2563EB`).
  - Assignment Badges: Global ("All Recruiters") vs. Individual Recruiter name.
  - Actions: Create Requisition modal, Edit, Mark Completed, Reopen, Archive, Safe Delete.

## 5.9 Service Client Management (`/clients`)
- **Purpose**: Full client customer lifecycle management.
- **Interactive Units**:
  - Filter Tabs: Active, Inactive, Archived, All.
  - Client Cards & Data Table: Company Name, Contact Person, Email, Phone, Ingested Resumes, Applications, Assigned Recruiter Avatars.
  - Actions: Create Client Modal, Assign/Unassign Recruiters Modal, Activate/Deactivate Toggle, Archive, Safe Delete.

## 5.10 Sub-Admin Delegation Center (`/sub-admins`)
- **Purpose**: Super Admin exclusive delegation of client accounts and recruiter teams.
- **Interactive Units**:
  - Sub-Admin Profile Cards: Name, Email, Status, Assigned Client tags, Assigned Recruiter tags.
  - Delegation Modal: Multi-select dropdowns for assigning Service Clients and Recruiters to Sub-Admins.

## 5.11 Targets & Quotas Hub (`/targets`)
- **Purpose**: Daily submission target configuration and historical compliance auditing.
- **Interactive Units**:
  - Target Matrix Table: Recruiter Name, Client Name, Daily Quota, Status (Active, Paused, Ended), Effective Date.
  - Actions: Set Target Modal, Pause Target, Resume Target, End Target, Delete (future targets only).

## 5.12 Analytics & Multi-Format Reports (`/reports`)
- **Purpose**: Enterprise data export and reporting engine.
- **Interactive Units**:
  - Multi-Sheet Excel Export (`.xlsx`): Downloads full client-by-client and recruiter-by-recruiter breakdown.
  - Branded PDF Executive Summary: Generates official PDF report with KPI summaries.
  - CSV Data Exports: Active Clients, Archived Clients, Inactive Staff, Completed Targets.

## 5.13 In-App Notification Center (`/notifications`)
- **Purpose**: Centralized operational feed for system, target, application, and chat events.
- **Interactive Units**:
  - Notification Rows: Title, Message, Category Icon, Relative Timestamp, Unread Indicator Dot.
  - Actions: Mark Single Read, Mark All Read, Clear Read Notifications Older Than 30 Days.

## 5.14 Performance & Architecture Telemetry (`/performance`)
- **Purpose**: Real-time engineering diagnostics and latency telemetry.
- **Interactive Units**:
  - In-Memory Cache Stats: Active cached keys, cache hit ratio, memory consumption.
  - SQL Profiler Telemetry: Average query count per route, average SQL latency in milliseconds, slow query alerts (`> 200ms`).

---

# Chapter 6 — Every UI Component Documentation

ApplyFlow utilizes an atomic, highly reusable UI component library located in `frontend/src/components/ui/`:

### 6.1 `Button.jsx`
- **Purpose**: Standard interactive button primitive supporting 6 distinct visual variants.
- **Variants**: `primary` (`#2563EB`), `secondary` (`#081226`), `outline` (border `#E2E8F0`), `ghost` (transparent hover), `danger` (`#EF4444`), `success` (`#16A34A`).
- **Sizes**: `sm` (height 36px), `md` (height 44px), `lg` (height 52px).
- **States**: `idle`, `hover`, `active`, `disabled`, `loading` (replaces label with inline spinner and sets `aria-busy="true"`).

### 6.2 `KPICard.jsx`
- **Purpose**: Hero telemetry card for key performance metrics.
- **Props**: `title`, `value`, `subtitle`, `icon`, `trend` (percentage string), `trendDirection` (`up` | `down`), `colorScheme` (`blue` | `orange` | `green` | `red` | `purple`).
- **Behavior**: Smooth hover elevation (`--shadow-card-hover`), animated counting transitions.

### 6.3 `ProgressRing.jsx`
- **Purpose**: SVG circular progress donut supporting over-achievement (> 100%).
- **Calculation**: Computes stroke-dasharray and stroke-dashoffset based on radius and percentage.
- **Color Shifts**:
  - `0% - 50%`: Danger Red (`#EF4444`)
  - `51% - 99%`: Progress Orange (`#F97316`)
  - `100%+`: Success Emerald (`#16A34A`) with pulsing glow.

### 6.4 `DateFilter.jsx`
- **Purpose**: Universal cascading date range selector.
- **Presets**: `Today`, `Yesterday`, `This Week`, `This Month`, `Custom Range`.
- **Behavior**: Emits normalized ISO date strings and handles instant cache invalidation.

### 6.5 `StatusBadge.jsx`
- **Purpose**: Semantic rounded badge for candidate pipeline and requirement stages.
- **Mappings**:
  - `Submitted` / `Applied`: Subtle Blue (`bg-[#EFF6FF] text-[#2563EB] border-[#BFDBFE]`)
  - `Shortlisted` / `Round 1` / `Round 2` / `Technical` / `Manager` / `HR`: Progress Purple / Orange
  - `Offer` / `Joined` / `Active` / `Met`: Success Green (`bg-[#F0FDF4] text-[#16A34A] border-[#BBF7D0]`)
  - `Rejected` / `Hold` / `Archived`: Danger Red / Slate Gray

### 6.6 `UploadDropzone.jsx`
- **Purpose**: Drag-and-drop batch ingestion staging container.
- **Behavior**: Handles drag-over highlights, client-side MIME validation (`application/pdf`), and file size enforcement (max 25MB per file).

### 6.7 `Table.jsx`
- **Purpose**: High-density sortable, paginated enterprise data table.
- **Features**: Sticky header row, zebra row hovering, integrated pagination controls, empty state fallback.

### 6.8 `Modal.jsx`
- **Purpose**: Accessible backdrop dialog.
- **Features**: Framer Motion entrance animation, full focus trap, `Esc` key dismissal, backdrop blur (`bg-black/60`).

### 6.9 `CommandPalette.jsx`
- **Purpose**: Global `⌘K` quick search and navigation launcher.
- **Features**: Keyboard navigation (Arrow keys, Enter, Esc), instant fuzzy searching across candidates, jobs, and clients.

### 6.10 `Toast.jsx`
- **Purpose**: Context-driven non-blocking notification engine.
- **Types**: `success` (Green), `error` (Red), `warning` (Orange), `info` (Blue) with auto-dismiss timer (4000ms).

---

# Chapter 7 — Every Modal Documentation

| Modal Name | Trigger Location | Fields & Inputs | Backend API Call | Success Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **Manual Upload Review Modal** | Upload Page (when file status is `needs_review`) | Candidate Name, Service Client, Target Company, Role, Resume ID Tag, Date | `POST /api/resumes/confirm-manual` | Files committed to DB & Drive; Confetti burst; Upload queue cleared. |
| **Create/Edit Client Modal** | Service Clients Page | Company Name, Contact Person, Email, Phone, Logo URL | `POST /api/clients` or `PUT /api/clients/{id}` | Client record saved; Cache invalidated; Table refreshed. |
| **Assign Recruiters Modal** | Service Clients Page | Multi-select Recruiter list, Primary Lead toggle | `POST /api/clients/{id}/employees` | `employee_clients` updated; In-app notification sent to recruiters. |
| **Create Requirement Modal** | Requirements Page | Client dropdown, Target Company, Role Title, Role Code, Job URL, Priority, Notes, Assignment Type | `POST /api/requirements` | Requisition created; Scoped recruiters notified. |
| **Set Daily Target Modal** | Targets Page / Recruiters Page | Recruiter dropdown, Client dropdown, Daily Target integer, Effective Date | `POST /api/targets` | Target created/updated; Dashboard recalculates quota. |
| **AI Extraction Confirm Modal** | Applications / AI Inbox | Editable Candidate, Company, Role, Status, Round, Interview Date, Matched Resume ID | `POST /api/ai/confirm-save` | Application pipeline updated; Event logged; Chat message posted. |
| **Resume Inline Preview Modal** | Candidate Studio / Chat | Read-only PDF viewer canvas, zoom controls, download action | `GET /api/resumes/{id}/preview` | Zero-leakage PDF rendered inline via secure stream. |
| **Resume Chat Share Modal** | Client Chat Window | Searchable resume dropdown from client's candidate bank | `POST /api/chat/rooms/{id}/share-resume` | Resume card attached into message stream via WebSocket. |

---

# Chapter 8 — Dashboard Architecture & Telemetry

ApplyFlow implements a unified dashboard bootstrap architecture that delivers sub-100ms dashboard rendering through role-specialized endpoints:

```
                                 GET /api/auth/bootstrap
                                            │
                      ┌─────────────────────┴─────────────────────┐
                      ▼                                           ▼
             Role Authorization                           Fast Cache Check
                      │                                           │
         ┌────────────┼────────────┐                              │
         ▼            ▼            ▼                              ▼
    Admin Home  Employee Home  Client Home               Sub-millisecond Return
```

## 8.1 Super Admin & Sub-Admin Dashboard Architecture
- **Single SQL Query Aggregation**: The admin overview executes all 14 metric calculations in a **single consolidated SQL query** using correlated subqueries, reducing database round-trips from 14 to 1.
- **Cascading Filter Engine**:
  - `client_id`: Scopes all metrics to a single Service Client.
  - `employee_id`: Scopes all metrics to a single Recruiter.
  - `date_range` / `custom_date`: Evaluates `resume_date` and `applied_date` dynamically for Today, Yesterday, This Week, This Month, or Custom Date.

## 8.2 Recruiter (Employee) Dashboard Architecture
- **Isolated Workspace Metrics**: Recruiters see only metrics for their assigned Service Clients.
- **Dynamic Quota Single Source of Truth**: Evaluates Applications Submitted today vs. Active Daily Target.

## 8.3 Service Client Dashboard Architecture
- **Customer Isolation**: Hard-scoped to `current_user.client_id`.
- **Metrics**: Total Candidates Available, Total Applications in Pipeline, Active Interview Stages, Chronological Event Activity Stream.

---

# Chapter 9 — Every Dashboard Card Specification

### 9.1 Today's Uploads Card
- **Purpose**: Measures candidate ingestion throughput for the active date.
- **Formula**: $\text{Count of Resumes where } \text{uploaded\_by} = \text{user.id} \text{ and } \text{resume\_date} = \text{target\_date}$
- **Color Scheme**: Blue (`#2563EB`).

### 9.2 Applications Submitted Card
- **Purpose**: Measures candidate delivery to hiring employers.
- **Formula**: $\text{Count of Applications where } \text{employee\_id} = \text{user.id} \text{ and } \text{applied\_date} = \text{target\_date}$
- **Color Scheme**: Orange (`#F97316`).

### 9.3 Daily Target Quota Card
- **Purpose**: Real-time quota fulfillment tracking.
- **Formula**:
  $$\text{Completion \%} = \left(\frac{\text{Applications Submitted}}{\text{Daily Target}}\right) \times 100$$
  $$\text{Remaining Work} = \max(\text{Daily Target} - \text{Applications Submitted}, 0)$$
- **Color Thresholds**:
  - $0\% - 50\%$: Danger Red (`#EF4444`)
  - $51\% - 99\%$: Progress Orange (`#F97316`)
  - $\ge 100\%$: Success Emerald (`#16A34A`)

### 9.4 Active Requisitions Card
- **Purpose**: Displays open hiring requisitions needing candidate submissions.
- **Formula**: $\text{Count of Requirements where } \text{status} = \text{'active'} \text{ and } \text{client\_id} \in \text{allowed\_clients}$

---

# Chapter 10 — Every Telemetry Chart Specification

All charts are rendered using Recharts and lazy-loaded via dedicated subcomponents (`AdminCharts`, `EmployeeCharts`, `ClientCharts`):

| Chart Name | Visual Type | Data Query & Calculations | Refresh Trigger |
| :--- | :--- | :--- | :--- |
| **Recruiter Target vs. Actual** | Grouped Bar Chart | Queries each recruiter's active target vs. total applications submitted for active date filter. | Filter change or batch upload. |
| **7-Day Velocity Curve** | Spline Area Chart | Calculates rolling 7-day daily completion percentage: $\frac{\sum \text{Submissions}_d}{\sum \text{Targets}_d} \times 100$. | Daily rollover or date filter. |
| **Client Volume Breakdown** | Horizontal Bar Chart | Groups total applications and resumes by `clients.company_name`. | New candidate upload / submission. |
| **Pipeline Stage Distribution** | Donut Chart | Aggregates application count by normalized stage (Submitted, Shortlisted, Technical, HR, Offer, Rejected). | Application status update. |

---

# Chapter 11 — Resume Ingestion & Storage System

## 11.1 Standard Filename Parser & Strict Verification
ApplyFlow enforces strict Service Client filename verification:

```text
Standard 3-Part:  ServiceClient_HiringCompany_Role.pdf
Standard 4-Part:  ServiceClient_HiringCompany_Role_CandidateName.pdf
Natural Resume:   CandidateName_Resume.pdf
```

### Validation Rules:
1. If structured format: Segment 0 (`ServiceClient`) is compared with the selected upload client.
   - If match $\rightarrow$ `status: "valid"`, `message: "ServiceClient Verified"`.
   - If mismatch $\rightarrow$ `status: "needs_review"`, `message: "ServiceClient Mismatch"`.
2. If natural candidate format: Automatically inherits the selected client $\rightarrow$ `status: "valid"`.

## 11.2 Pre-Commit Duplicate Detection Engine
Before any file is written to storage or database, `POST /api/resumes/check-duplicates` scans the client's candidate bank:
- Checks exact `resume_id_tag` match (e.g. `RES101`).
- Checks exact `candidate_name` + `company` combination.
- Duplicate rows are highlighted in Amber (`#FFFBEB`) with existing candidate details.

## 11.3 Dual Storage Architecture (Google Drive + Local Fallback)

```
Recruiter Uploads PDF
        │
        ▼
Fast Local Disk Write (./uploads/)  ➔  Sub-millisecond API response
        │
        ▼ (Background Task)
Google Apps Script Web App API  ➔  Personal Google Drive (Root Folder ID)
        │
        ▼
Resume Record Updated with Google Drive File ID
```

---

# Chapter 12 — Candidate Bank & Split-Screen Studio

The Candidate Studio (`/candidates`) allows rapid candidate evaluation without tab switching:
- **Zero-Leakage PDF Streamer**: Streams binary bytes directly using `FastAPIResponse(content=file_bytes, media_type="application/pdf")`. Public Google Drive URLs are never exposed in browser DOM.
- **Client Note Sharing**: Recruiter notes can be marked private or shared with client (`is_note_shared=true`).

---

# Chapter 13 — Application Pipeline & Stage Transitions

## 13.1 Pipeline State Machine

```
   [ Draft / Unsubmitted ]
              │ (Direct Submit or Batch Upload)
              ▼
        [ Submitted ]
              │
    ┌─────────┴─────────┐
    ▼                   ▼
[ Shortlisted ]    [ Rejected ]
    │
    ▼
[ Round 1 / Technical ]
    │
    ▼
[ Round 2 / Manager ]
    │
    ▼
[ HR Round ]
    │
    ▼
 [ Offer Letter ]
    │
    ▼
  [ Joined ] ──► [ Closed / Archived ]
```

---

# Chapter 14 — Groq AI Interview Intake Engine

Powered by **Groq LLaMA 3.3 70B** (`temperature=0.0`), the AI Inbox transforms messy interview invitation emails into structured updates in seconds.

## 14.1 Two-Phase Intake Architecture
1. **Phase 1 (Preview Only)**: `POST /api/ai/analyze-email` or `/api/ai/analyze-file` parses text without writing to database or chat.
2. **Phase 2 (Confirm & Save)**: `POST /api/ai/confirm-save` executes database transactions, links resumes, appends audit events, and updates client chat.

## 14.2 4-Tier Smart Resume Linking Algorithm

```
                  Unstructured Interview Email Received
                                    │
                                    ▼
                Extract: Candidate, Company, Role, Tag
                                    │
                                    ▼
       ┌────────────────────────────────────────────────────────┐
       │ Priority 1: Exact Resume Tag Match (e.g. RES101) ?     │──[YES]──► Link Resume
       └────────────────────────────┬───────────────────────────┘
                                    │ [NO]
                                    ▼
       ┌────────────────────────────────────────────────────────┐
       │ Priority 2: Exact Candidate Name + Hiring Company ?   │──[YES]──► Link Resume
       └────────────────────────────┬───────────────────────────┘
                                    │ [NO]
                                    ▼
       ┌────────────────────────────────────────────────────────┐
       │ Priority 3: Exact Candidate Name + Role Designation ? │──[YES]──► Link Resume
       └────────────────────────────┬───────────────────────────┘
                                    │ [NO]
                                    ▼
       ┌────────────────────────────────────────────────────────┐
       │ Priority 4: Fallback (Save record with resume_id=null) │
       └────────────────────────────────────────────────────────┘
```

---

# Chapter 15 — Real-Time Role-Based Chat

- **Topology**: Exactly one chat room per Service Client (`chat_rooms`).
- **WebSocket Protocol**: `/api/chat/ws/{room_id}` delivers real-time messages, typing indicators, read receipts, and resume attachments.
- **Cursor Read Tracking**: `chat_reads` stores `last_read_message_id`. Unread count is calculated as $\text{Count of messages where } \text{created\_at} > \text{cursor.created\_at}$.

---

# Chapter 16 — In-App Notification System

Notifications are generated asynchronously for critical business triggers:
- `upload_completed`: Dispatched to uploader, assigned admins, and client users.
- `interview_email_confirmed`: Dispatched when an AI intake event is confirmed.
- `target_achieved`: Dispatched when recruiter reaches 100% daily quota.

---

# Chapter 17 — Shift Attendance & Time Tracking

- **Check-In**: `POST /api/attendance/check-in` creates a workday record with `check_in = NOW()`.
- **Check-Out**: `POST /api/attendance/check-out` sets `check_out = NOW()` and computes `total_hours` (e.g. `"7h 45m"`).
- **Live Ticker**: Frontend recalculates elapsed time every second while session is active.

---

# Chapter 18 — Requirements & Requisitions Matrix

- **Assignment Modes**:
  - `assignment_type = "all"`: Visible to all recruiters assigned to the Service Client.
  - `assignment_type = "individual"`: Assigned exclusively to `assigned_employee_id`.
- **Completion Rules**: Marking as done sets `completed_by` and `completed_at` while preserving candidate submission history.

---

# Chapter 19 — Targets & Quota Engine

- **Entity**: `targets` table binds `(employee_id, client_id, effective_date)` with unique constraint.
- **Lifecycle States**:
  - `active`: Enforced in daily calculations.
  - `paused`: Suspended temporarily.
  - `ended`: Concluded for historical auditing.
- **Deletion Rule**: Targets can only be deleted *before* their `effective_date`. Past targets must be ended to maintain audit history.

---

# Chapter 20 — Database Dictionary & Schema Specifications

```sql
-- Core Entities Summary
users                    (id UUID PK, name, email, role, client_id, status, is_active)
clients                  (id UUID PK, company_name, contact_person, email, status, is_active)
employee_clients         (id UUID PK, employee_id FK, client_id FK, is_primary, active)
sub_admin_assignments    (id UUID PK, sub_admin_id FK, employee_id FK, client_id FK, active)
resumes                  (id UUID PK, candidate_name, company, role, resume_id_tag, client_id FK, drive_file_id)
requirements             (id UUID PK, client_id FK, company, role, role_code, priority, status)
applications             (id UUID PK, resume_id FK, employee_id FK, client_id FK, status, current_round)
application_events       (id UUID PK, application_id FK, event_type, round_name, raw_email, ai_json)
email_intake             (id UUID PK, uploaded_by FK, client_id FK, original_text, source_type)
targets                  (id UUID PK, employee_id FK, client_id FK, daily_target, status, effective_date)
attendance               (id UUID PK, employee_id FK, work_date, check_in, check_out, total_hours)
chat_rooms               (id UUID PK, client_id FK UNIQUE, status)
chat_messages            (id UUID PK, room_id FK, sender_id FK, message, attachment_type, attachment_reference)
chat_reads               (id UUID PK, user_id FK, room_id FK, last_read_message_id FK)
notifications            (id UUID PK, user_id FK, title, message, type, is_read)
activity_logs            (id UUID PK, user_id FK, action, details JSON, created_at)
```

---

# Chapter 21 — REST API & WebSocket Reference

All endpoints are registered under `/api/` in `backend/app/main.py`:
- `auth`: `/api/auth/login`, `/refresh`, `/logout`, `/me`, `/bootstrap`
- `resumes`: `GET/POST /api/resumes`, `/upload`, `/check-duplicates`, `/find-match`, `/{id}/preview`, `/{id}/download`
- `applications`: `GET/POST /api/applications`, `/{id}/timeline`, `/{id}/close`, `/{id}/archive`, `DELETE /{id}`
- `ai`: `POST /api/ai/analyze-email`, `/analyze-file`, `/confirm-save`, `GET /inbox`
- `clients`: `GET/POST /api/clients`, `PUT/PATCH /{id}`, `/{id}/activate`, `/{id}/deactivate`, `/{id}/archive`, `/{id}/employees`
- `targets`: `GET/POST /api/targets`, `/{id}/pause`, `/{id}/resume`, `/{id}/end`, `/progress`
- `attendance`: `GET /api/attendance/status`, `POST /check-in`, `POST /check-out`, `GET /admin-summary`
- `chat`: `GET /api/chat/rooms`, `GET/POST /rooms/{id}/messages`, `POST /share-resume`, `POST /read`, `WS /api/chat/ws/{id}`
- `reports`: `GET /api/reports/excel`, `/pdf`, `/export/clients`, `/export/employees`, `/export/targets`
- `notifications`: `GET /api/notifications`, `POST /{id}/read`, `POST /read-all`, `DELETE /{id}`
- `activity_logs`: `GET /api/activity-logs`

---

# Chapter 22 — Backend Architecture & Service Layer Design

The backend uses a strict layered architecture:
1. **Router Layer (`router.py`)**: Request validation, Pydantic schema deserialization, dependency injection.
2. **Service Layer (`service.py`)**: Authoritative owner of business logic, multi-tenant scoping, transaction orchestration, and cache invalidation.
3. **Model Layer (`models.py`)**: Declarative SQLAlchemy 2.0 ORM mappings with explicit relationships and composite indexes.
4. **Core Infrastructure (`app/core/`)**: Connection pool management, JWT cookie generation, telemetry middleware, and in-memory TTL caching.

---

# Chapter 23 — Frontend Architecture, SWR Caching & State

The React frontend utilizes a high-performance Stale-While-Revalidate (SWR) in-memory cache implemented directly in `frontend/src/services/api.js`:
- **Inflight Promise Deduplication**: Identical concurrent requests share a single network promise.
- **Deterministic Scoped Invalidation**: Mutations (e.g. `POST /api/resumes/upload`) trigger `invalidateScopedCache('/resumes')`, which purges cached entries across resumes, dashboard, and reports.
- **Auth Interceptor**: 401 errors automatically trigger a silent refresh attempt against `/api/auth/refresh` before retrying the original request.

---

# Chapter 24 — Environment Variables & Runtime Configuration

| Variable | Purpose | Default / Production Recommendation |
| :--- | :--- | :--- |
| `USE_SQLITE` | Toggles SQLite for local zero-config testing. | `False` (PostgreSQL/Neon in production) |
| `DATABASE_URL_OVERRIDE` | Asynchronous database connection string. | `postgresql+asyncpg://user:pass@host/db?ssl=require` |
| `JWT_SECRET_KEY` | Cryptographic secret for signing tokens. | Minimum 32-character high-entropy random string |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Lifetime of access token. | `60` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Lifetime of refresh token cookie. | `7` |
| `GROQ_API_KEY` | API key for Groq LLaMA 3.3 AI engine. | `gsk_...` |
| `GOOGLE_APPS_SCRIPT_URL` | Web App URL for Google Drive storage. | `https://script.google.com/macros/s/.../exec` |
| `GOOGLE_DRIVE_ROOT_FOLDER_ID`| Root folder ID in Google Drive. | `11N7TFi1dQ98L9TRgV87966JAliQ5jcIq` |
| `FRONTEND_URL` | Allowed origin for CORS headers. | `https://workspace.applyflow.com` |

---

# Chapter 25 — Performance Architecture & Telemetry

- **SQL Composite Indexing**: 18 indexes defined in migration `a1b2c3d4e5f6_performance_indexes.py` optimize candidate search, date-range filtering, and unread notification lookups.
- **Profiler Middleware**: Every request is measured for execution time, query count, and SQL duration. Slow requests exceeding 200ms trigger immediate console alerts.
- **Connection Pre-Warming**: `warmup_db_pool()` issues a test query on server startup to eliminate cold-start database latency.

---

# Chapter 26 — Security Architecture

- **Dual HTTP-Only Cookies**: Access and refresh tokens are stored in `httponly=True` cookies, making them completely inaccessible to client-side JavaScript and immune to XSS token theft.
- **Multi-Tenant Customer Isolation**: Every query in the service layer enforces `get_allowed_client_ids(db, current_user)` to prevent Insecure Direct Object References (IDOR).
- **SQL Injection Prevention**: 100% of database interactions utilize parameterized SQLAlchemy ORM queries or bound text parameters.

---

# Chapter 27 — Testing Strategy & QA Verification

The system includes a comprehensive suite of automated tests located in `backend/`:
- `test_master_qa_suite.py`: Complete end-to-end integration and smoke test suite.
- `test_all_modules.py`: Cross-module regression tests covering Auth, Resumes, AI Inbox, Chat, Attendance, and Reports.
- `test_smart_resume_linking.py`: Validates 4-tier Groq matching algorithm under various edge-case filename structures.
- `test_applications_permissions.py`: Verifies RBAC boundaries and IDOR isolation.
- `test_apps_script_storage.py`: Validates Google Drive storage integration and local disk fallback.

---

# Chapter 28 — Current Implementation Audit & Parity Matrix

| System Component | Implementation Status | Notes |
| :--- | :---: | :--- |
| **Authentication & Dual JWT Cookies** | Complete | HTTP-only cookies with Bearer fallback and background dashboard pre-warming. |
| **Bulk Resume Ingestion (1–100+)** | Complete | Strict Service Client tokenizer, pre-commit duplicate check, Drive + local fallback. |
| **Groq AI Interview Mail Intake** | Complete | 2-phase preview/confirm architecture with 4-tier smart resume linking. |
| **Daily Target Quota Engine** | Complete | Real-time calculation based on submitted applications, status pausing/ending. |
| **Real-Time Role-Based Chat** | Complete | WebSocket broadcasting, resume attachments, cursor read tracking. |
| **Shift Attendance & Session Timer** | Complete | Check-in, check-out, live running timer, admin live roster. |
| **Client & Sub-Admin Management** | Complete | Scoped delegation, lifecycle state transitions, safe deletion rules. |
| **Multi-Format Export Engine** | Complete | Multi-sheet Excel (`.xlsx`), branded PDF summary, CSV exports. |
| **In-Memory SWR Caching & Profiler** | Complete | Tag-based cache invalidation, query count and latency headers. |

---
*Prepared by the Chief Product Architect & Principal Engineering Team for ApplyFlow Enterprise Operations.*
