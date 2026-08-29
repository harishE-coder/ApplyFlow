# ApplyFlow ATS — UI/UX Design System & Experience Architecture Specification

> **Document Version**: 2.0.0  
> **Target Audience**: Product Designers, Frontend Engineers, SDETs, UI/UX Specialists  
> **Core Stack**: React 18, Vite 6, Tailwind CSS v4, Framer Motion, Lucide React, FastAPI, Groq AI (LLaMA 3.3 70B), Google Apps Script

---

## 1. Executive Product & UX Strategy

### 1.1 Product Identity & Design Philosophy
**ApplyFlow** is a modern, high-velocity recruitment workspace engineered specifically for recruitment agencies, staffing firms, and Talent Operations teams.

The design philosophy balances **enterprise density** with **consumer-grade polish**:
- **High-Density Data Scanning**: Recruiters process hundreds of resumes daily. Data displays are compact, scannable, and clean without feeling cluttered.
- **Glassmorphism & Ambient Depth**: Deep navy sidebars (`#081226`), crisp white surfaces (`#FFFFFF`), subtle borders (`#E2E8F0`), and soft backdrop blurs (`backdrop-blur-md`) establish visual hierarchy.
- **Cognitive Clarity**: Strict separation between **Service Clients** (our paying staffing customers) and **Hiring Companies** (end-client employers e.g., Amazon, TCS, Google).
- **Proactive AI Ergonomics**: Groq LLaMA 3.3 parses unstructured interview invite emails and auto-links them to candidates using a 4-tier matching algorithm.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             APPLYFLOW ECOSYSTEM                             │
├──────────────────────────┬──────────────────────────┬───────────────────────┤
│    SERVICE CLIENTS       │     HIRING COMPANIES     │      RECRUITERS       │
│  (Paying Staffing Orgs)  │   (Target Employers)     │ (Dedicated Specialists│
│  e.g., ABC Staffing      │  e.g., Google, TCS, Meta │   Managing Clients)   │
└──────────────────────────┴──────────────────────────┴───────────────────────┘
```

---

## 2. Design System & Visual Tokens

### 2.1 Color Palette

```
/* Primary Navy Foundations (Dark UI, Sidebar, Elevated Modals) */
--color-navy:                  #081226;   /* Primary Dark Theme Base */
--color-navy-dark:             #040A17;   /* Deep Container Base */
--color-navy-light:            #101F3D;   /* Interactive Hover / Subnav */
--color-navy-border:           #1E2E4E;   /* Dark Structural Borders */

/* Brand & Interactive Colors */
--color-blue-primary:          #2563EB;   /* Primary Actions, Active State */
--color-blue-hover:            #1D4ED8;   /* Button Hover */
--color-blue-subtle:           #EFF6FF;   /* Soft Blue Badges & Tinted Rows */
--color-blue-border:           #BFDBFE;   /* Blue Accent Borders */

/* Progress & Live Target Highlights */
--color-orange-progress:       #F97316;   /* Milestone Highlights & Quota Ring */
--color-orange-subtle:         #FFF7ED;   /* Warning / Target Badges */
--color-orange-border:         #FFEDD5;   /* Orange Accent Borders */

/* Neutral Workspace Foundations */
--color-bg-main:               #F6F8FB;   /* Canvas Background */
--color-surface-white:         #FFFFFF;   /* Primary Card Surfaces */
--color-surface-muted:         #F8FAFC;   /* Table Headers / Filter Strips */
--color-surface-border:        #E2E8F0;   /* Light Structural Dividers */
--color-surface-border-subtle: #F1F5F9;   /* Inner Item Separators */

/* Status & Semantic Signals */
--color-status-success:        #16A34A;   /* Green (Target Met >= 100%, Approved) */
--color-status-success-bg:     #F0FDF4;
--color-status-success-border: #BBF7D0;

--color-status-warning:        #F59E0B;   /* Amber / Orange (Target 51-99%, Review) */
--color-status-warning-bg:     #FFFBEB;
--color-status-warning-border: #FDE68A;

--color-status-danger:         #EF4444;   /* Red (Target 0-50%, Reject, Error) */
--color-status-danger-bg:      #FEF2F2;
--color-status-danger-border:  #FECACA;

/* High-Contrast Typography Tokens */
--color-text-main:             #081226;   /* High-Contrast Headers & Body */
--color-text-secondary:        #475569;   /* Sub-labels & Field Titles */
--color-text-muted:            #94A3B8;   /* Placeholders, Inactive Icons */
--color-text-dim:              #CBD5E1;   /* Disabled State & Subtle Dividers */
```

### 2.2 Quota & Target Color Thresholds
Targets are evaluated dynamically using Applications Submitted vs. Daily Target:

$$\text{Completion \%} = \left(\frac{\text{Applications Submitted}}{\text{Daily Target}}\right) \times 100$$

| Completion Range | Visual State | Color Token | Hex Code | Semantic Indicator |
| :--- | :--- | :--- | :--- | :--- |
| **0% – 50%** | Critical / At Risk | Danger Red | `#EF4444` | Immediate attention required |
| **51% – 99%** | In Progress | Progress Orange | `#F97316` | On track toward daily goal |
| **100%+** | Goal Achieved | Success Emerald | `#16A34A` | Daily target met / overachieved |

---

### 2.3 Typography Scale

Primary Typeface: **Inter**, `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `sans-serif`.  
Monospace Typeface: `ui-monospace`, `SFMono-Regular`, `Menlo`, `Monaco`, `Consolas`, `monospace` (used for Resume ID tags like `RES101`, timestamps, code snippets).

```
┌─────────────────┬───────────┬──────────────┬────────────┬──────────────────────────────────────┐
│ Typography Role │ Font Size │ Line Height  │ Weight     │ Tracking / Letter Spacing            │
├─────────────────┼───────────┼──────────────┼────────────┼──────────────────────────────────────┤
│ Display         │ 40px      │ 48px (1.20)  │ 800 (Extra)│ -0.025em (Hero Stats & Timers)       │
│ Heading 1 (h1)  │ 32px      │ 40px (1.25)  │ 700 (Bold) │ -0.020em (Page Titles)               │
│ Heading 2 (h2)  │ 24px      │ 32px (1.33)  │ 600 (Semi) │ -0.015em (Card Headers, Section Top) │
│ Heading 3 (h3)  │ 20px      │ 28px (1.40)  │ 600 (Semi) │ -0.010em (Sub-sections, Modal Heads) │
│ Body Regular    │ 16px      │ 24px (1.50)  │ 400 (Reg)  │ Normal (Inputs, Long Descriptions)   │
│ Body Small      │ 14px      │ 20px (1.43)  │ 500 (Med)  │ Normal (Table Rows, Filter Options)  │
│ Caption / Meta  │ 12px      │ 16px (1.33)  │ 600 (Semi) │ +0.010em (Badges, Timestamps, Tags)  │
│ Micro Tag       │ 10px-11px │ 14px (1.27)  │ 700 (Bold) │ +0.050em (Uppercase Category Labels) │
└─────────────────┴───────────┴──────────────┴────────────┴──────────────────────────────────────┘
```

---

### 2.4 Elevation & Depth (Shadow Scale)

- **Card Elevation (`--shadow-card`)**: `0 1px 3px rgba(8, 18, 38, 0.04), 0 4px 12px rgba(8, 18, 38, 0.03)`
- **Card Hover Elevation (`--shadow-card-hover`)**: `0 4px 14px rgba(8, 18, 38, 0.08), 0 1px 3px rgba(8, 18, 38, 0.04)`
- **Sidebar Float Elevation (`--shadow-sidebar`)**: `0 20px 40px -12px rgba(8, 18, 38, 0.28), 0 4px 16px rgba(8, 18, 38, 0.12)`
- **TopBar Glass Elevation (`--shadow-topbar`)**: `0 4px 20px -4px rgba(8, 18, 38, 0.05)`
- **Dropdown & Popover Elevation (`--shadow-dropdown`)**: `0 10px 30px -4px rgba(8, 18, 38, 0.15), 0 2px 6px rgba(8, 18, 38, 0.05)`
- **Drawer Slide-out (`--shadow-drawer`)**: `-8px 0 32px rgba(8, 18, 38, 0.12)`

---

## 3. Global Information Architecture & Navigation

### 3.1 Shell Layout Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  APPLYFLOW GLOBAL APPLICATION FRAME                                                                    │
├─────────────────────────┬──────────────────────────────────────────────────────────────────────────────┤
│  PERSISTENT SIDEBAR     │  FROSTED GLASS TOPBAR                                                        │
│  (Desktop: 280px Wide   │  [Menu] [Brand] [Search Candidates, Jobs... (⌘K)] [Date] [Shift] [🔔] [User] │
│   Dark Navy #081226     ├──────────────────────────────────────────────────────────────────────────────┤
│   Rounded 28px Float)   │  DYNAMIC PAGE OUTLET (Responsive Padding: px-3 sm:px-5 lg:px-6)              │
│                         │                                                                              │
│  [ ApplyFlow Logo ]     │  - Admin Operations Command Center                                           │
│                         │  - Recruiter Workspace & Ingestion Hub                                       │
│  CORE WORKSPACE         │  - Candidate Studio (Split-Screen View)                                      │
│  - Dashboard            │  - Groq AI Response Inbox & Email Intake                                     │
│                         │  - Client Service Portal                                                     │
│  RECRUITMENT            │  - Real-Time WebSocket Chat                                                  │
│  - Upload Resumes       │  - Analytics, Targets & Multi-Format Exports                                 │
│  - Candidates           │                                                                              │
│  - Applications (AI)    │                                                                              │
│  - Chats [Badge]        │                                                                              │
│  - Job Openings         │                                                                              │
│                         │                                                                              │
│  MANAGEMENT             │                                                                              │
│  - Service Clients      │                                                                              │
│  - Sub-Admins           │                                                                              │
│  - Recruiters           │                                                                              │
│  - Targets & Goals      │                                                                              │
│                         │                                                                              │
│  INSIGHTS               │                                                                              │
│  - Reports & Analytics  │                                                                              │
│  - Notifications        │                                                                              │
│                         │                                                                              │
│  [ Recruiter Session ]  │                                                                              │
│  [ Profile & Sign Out ] │                                                                              │
└─────────────────────────┴──────────────────────────────────────────────────────────────────────────────┘
```

---

### 3.2 Role-Based Access Control (RBAC) Navigation Matrix

| Navigation Item | Route | Super Admin | Sub-Admin | Recruiter (Employee) | Service Client |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Dashboard** | `/dashboard` | Global Analytics | Scoped Analytics | Personal Workspace | Customer Portal |
| **Upload Resumes** | `/upload` | ❌ *(Protected)* | ❌ *(Protected)* | ✅ *(Ingestion Engine)* | ❌ *(Protected)* |
| **Candidate Studio** | `/candidates` | ✅ (All Resumes) | ✅ (Scoped Resumes) | ✅ (Assigned Resumes) | ✅ (Client's Talent) |
| **Applications (AI)** | `/applications` | ✅ (All Inboxes) | ✅ (Scoped Inboxes) | ✅ (Assigned Pipeline)| ✅ (Client Timeline) |
| **Live Chat** | `/chats` | ✅ (System-wide) | ✅ (Scoped Rooms) | ✅ (Client Rooms) | ✅ (Recruiter Room) |
| **Job Openings** | `/requirements` | ✅ (Full Control) | ✅ (Scoped Jobs) | ✅ (Assigned Openings)| ✅ (Requisitions) |
| **Service Clients** | `/clients` | ✅ (Full Admin) | ✅ (Scoped Clients) | ✅ (View Assigned) | ❌ |
| **Sub-Admins** | `/sub-admins` | ✅ (Full Admin) | ❌ | ❌ | ❌ |
| **Recruiters** | `/recruiters` | ✅ (Full Admin) | ✅ (Scoped Team) | ❌ | ❌ |
| **Targets & Goals** | `/targets` | ✅ (Set & Modify)| ✅ (Scoped Targets) | ✅ (View Quotas) | ❌ |
| **Reports & Exports**| `/reports` | ✅ (Excel/PDF/CSV) | ✅ (Scoped Exports) | ✅ (Export View) | ✅ (Client PDF) |
| **Notifications** | `/notifications`| ✅ | ✅ | ✅ | ✅ |

---

## 4. Detailed Workspace Page Specifications

---

### 4.1 Authentication & Login Portal (`/login`)

```
┌──────────────────────────────────────────────────────────┬──────────────────────────────────────────────────────────┐
│  LEFT 42%: BRANDING & VALUE SHOWCASE                     │  RIGHT 58%: HIGH-PRECISION LOGIN CARD                    │
│  (Dark Navy #081226 Background with Ambient Glow)        │  (Crisp Surface, Max-width 480px, Centered)              │
│                                                          │                                                          │
│  [ ApplyFlow Brand Logo ]                                │  Sign in to workspace                                    │
│                                                          │  Enter your corporate credentials to access pipelines.   │
│  ⚡ ENTERPRISE RECRUITMENT ATS                           │                                                          │
│  Recruitment operations at scale.                        │  ┌────────────────────────────────────────────────────┐  │
│  Precision candidate parsing, live pipeline              │  │ Work Email Address                                 │  │
│  orchestration, client delivery tracking, and            │  │ [✉] recruiter@applyflow.com                       │  │
│  performance targets in one unified workspace.           │  └────────────────────────────────────────────────────┘  │
│                                                          │                                                          │
│  [ ATS Multi-layer Feature Graphic ]                     │  ┌────────────────────────────────────────────────────┐  │
│                                                          │  │ Password                                           │  │
│  ✓ Multi-client candidate isolation & scoping            │  │ [🔒] ••••••••••••                                   │  │
│  ✓ Instant batch resume ingestion & duplicate detection  │  └────────────────────────────────────────────────────┘  │
│  ✓ Permanent split-view candidate review & workflow      │                                                          │
│                                                          │  ┌────────────────────────────────────────────────────┐  │
│  ApplyFlow ATS • Enterprise Edition                      │  │ [ Sign In to ApplyFlow                          → ]│  │
│                                                          │  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┴──────────────────────────────────────────────────────────┘
```

- **Micro-Interactions**:
  - Ambient radial gradients (`bg-[#2563EB]/15` and `bg-[#F97316]/10`) animate softly in the branding pane.
  - Form validation errors render inline with shake animations (`x: [-4, 4, -4, 4, 0]`).
  - Active submission button triggers animated spinner with accessible `aria-busy="true"`.

---

### 4.2 Recruiter (Employee) Workspace (`/dashboard`)

The flagship workspace for talent specialists is divided into a **70% Left / 30% Right** split canvas:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  RECRUITER WORKSPACE HEADER                                                                                            │
│  Active Recruiter: Harish • Assigned Service Client Filter: [ All Assigned Clients (3) ▾ ] • Date: [ Today (Active) ▾ ] │
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  KPI STRIP                                                                                                             │
│  ┌──────────────────────┬──────────────────────┬──────────────────────┬─────────────────────────────────────────────┐  │
│  │ Today's Uploads      │ Applications Done    │ Daily Target Quota   │ Target Completion %                         │  │
│  │ 35 Resumes           │ 28 Submitted         │ 28 / 25 Submissions  │ 112% (🎯 100% Target Met!)                  │  │
│  │ [+12 from yesterday] │ [Delivered to Client]│ [Quota: 25 Daily]    │ [Green High-Performance Badge]              │  │
│  └──────────────────────┴──────────────────────┴──────────────────────┴─────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────┤
│  LEFT COLUMN (70% WIDTH - INGESTION & PIPELINE)              │  RIGHT COLUMN (30% WIDTH - TELEMETRY & ATTENDANCE)      │
│                                                              │                                                         │
│  1. BATCH RESUME DROPZONE (HERO COMPONENT)                   │  1. DAILY TARGET PROGRESS DONUT                         │
│  ┌────────────────────────────────────────────────────────┐  │  ┌───────────────────────────────────────────────────┐  │
│  │ FAST INGESTION ENGINE                                  │  │  │ DAILY TARGET QUOTA: 112%                          │  │
│  │ Drag & drop candidate PDF resumes here                 │  │  │                                                   │  │
│  │ Standard Format: ServiceClient_Company_Role_ID.pdf     │  │  │                 ╭─────────────╮                   │  │
│  │                                                        │  │  │              ╭──╯             ╰──╮                │  │
│  │   [ ☁ Cloud Upload Icon ]                              │  │  │             │     28 / 25     │  [Donut Ring]     │  │
│  │   Drop 1 to 100+ files or [ Browse Files ]             │  │  │              ╰──╮             ╭──╯                │  │
│  │                                                        │  │  │                 ╰─────────────╯                   │  │
│  │   • Pre-commit duplicate check runs automatically      │  │  │                                                   │  │
│  │   • Entity extraction parses tokens before commit      │  │  │  Target: 25 • Done: 28 • Over-achieved: +3        │  │
│  └────────────────────────────────────────────────────────┘  │  └───────────────────────────────────────────────────┘  │
│                                                              │                                                         │
│  2. RECRUITER 7-DAY PERFORMANCE TREND (CHART)                │  2. SHIFT ATTENDANCE & LIVE SESSION TIMER               │
│  [ Daily Submissions Bar Chart with Target Quota Threshold ] │  ┌───────────────────────────────────────────────────┐  │
│                                                              │  │ ACTIVE SHIFT DURATION                             │  │
│  3. ACTIVE CLIENT REQUIREMENTS (OPEN SLOTS)                  │  │ 04:32:18 (Started at 09:00 AM)                    │  │
│  - TCS • Senior Java Developer (8 open slots)                │  │ [ ⏹ End Shift Session ]                           │  │
│  - Infosys • Python Backend Engineer (4 open slots)          │  └───────────────────────────────────────────────────┘  │
│                                                              │                                                         │
│  4. GROQ AI EMAIL INBOX TELEMETRY                            │  3. PERSONAL ACTIVITY STREAM                            │
│  [18 Emails Processed] [12 New Apps] [5 Interviews Today]    │  • 10:14 AM: Uploaded 22 resumes for ABC Staffing    │  │
│                                                              │  • 11:30 AM: Submitted Rahul Kumar to TCS            │  │
└──────────────────────────────────────────────────────────────┴─────────────────────────────────────────────────────────┘
```

---

### 4.3 Super Admin Operations & Quota Center (`/dashboard`)

Administrators monitor cross-client operations, recruiter leaderboards, and target compliance:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  ADMIN COMMAND BAR (4 REACTIVE CASCADING FILTERS)                                                                      │
│  1. Service Client: [ All Clients (12) ▾ ]  2. Recruiter: [ All Recruiters (8) ▾ ]  3. Date: [ Today / Range Filter ▾ ] │
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  GLOBAL TELEMETRY CARDS                                                                                                │
│  [Daily Target: 180] [Submitted: 164] [Completion: 91%] [Remaining: 16] [Active Staff: 8] [Sub-Admins: 2]              │
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  RECRUITER-WISE TARGET LEADERBOARD TABLE (LIVE THROUGHPUT)                                                             │
│                                                                                                                        │
│  Recruiter               Daily Target    Submitted    Remaining    Completion % & Visual Progress Bar                  │
│  ──────────────────────  ────────────    ─────────    ─────────    ──────────────────────────────────                  │
│  👤 Priya Sharma (Lead)       35            38           0         [████████████████████] 108% (Green Met)             │
│  👤 Rahul Verma               25            24           1         [████████████████░░░░]  96% (Orange In-Progress)   │
│  👤 Sneha Patil               30            12          18         [████████░░░░░░░░░░░░]  40% (Red Below-Quota)       │
│  👤 Vikram Seth               25            25           0         [████████████████████] 100% (Green Met)             │
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  4 INTERACTIVE TELEMETRY CHARTS (RECHARTS INTEGRATION)                                                                 │
│  ┌──────────────────────────────────────────────┐  ┌────────────────────────────────────────────────────────┐          │
│  │ 1. Recruiter Target vs Actual Submissions    │  │ 2. 7-Day Company Target Completion Velocity            │          │
│  │ (Grouped Bar Chart: Target vs. Done)         │  │ (Smooth Spline Area Chart: Target % Curve)             │          │
│  ├──────────────────────────────────────────────┤  ├────────────────────────────────────────────────────────┤          │
│  │ 3. Client Performance Breakdown              │  │ 4. Application Pipeline Stage Distribution             │          │
│  │ (Horizontal Bar Chart: Submissions per Org)  │  │ (Donut Chart: Shortlisted, Interview, Offer, Rejected) │          │
│  └──────────────────────────────────────────────┘  └────────────────────────────────────────────────────────┘          │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### 4.4 Candidate Studio & Resume Management (`/candidates`)

The Candidate Studio uses a **Master-Detail Split-Screen Layout** to allow fast evaluation without tab-switching:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  CANDIDATE STUDIO                                                                                                      │
│  Search: [🔍 Name, role, resume tag... ] • Client: [ All Clients ▾ ] • Target Company: [ All ▾ ] • Date: [ Today ▾ ]   │
├──────────────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────┤
│  LEFT 40%: CANDIDATE FEED LIST (PAGE SIZE: 20)               │  RIGHT 60%: ZERO-LEAKAGE PROTECTED PDF STREAMER         │
│                                                              │                                                         │
│  ┌────────────────────────────────────────────────────────┐  │  ┌───────────────────────────────────────────────────┐  │
│  │ [Selected] Rahul Kumar                        [RES101] │  │  │ Candidate: Rahul Kumar • TCS (Java Developer)     │  │
│  │ TCS • Senior Java Developer • ABC Staffing             │  │  │ Resume ID: RES101 • Uploaded: Today at 10:14 AM   │  │
│  │ Status: [ Shortlisted ] • Applied: Today               │  │  │ [ ⬇ Download PDF ] [ ✉ AI Link ] [ 💬 Share Chat ] │  │
│  ├────────────────────────────────────────────────────────┤  │  ├───────────────────────────────────────────────────┤  │
│  │ Priya Sundaram                                [RES102] │  │  │                                                   │  │
│  │ Infosys • Fullstack React Developer                    │  │  │   [ SECURE PDF INLINE STREAMING CONTAINER ]       │  │
│  │ Status: [ Interview Scheduled ]                        │  │  │   - Rendered directly via Google Drive Stream API │  │
│  ├────────────────────────────────────────────────────────┤  │  │   - Zero public URL leakage                       │  │
│  │ Amit Patel                                    [RES103] │  │  │   - Interactive Zoom & Page Navigation Controls   │  │
│  │ Amazon • SDE II (Backend)                              │  │  │                                                   │  │
│  │ Status: [ Under Review ]                               │  │  │                                                   │  │
│  └────────────────────────────────────────────────────────┘  │  └───────────────────────────────────────────────────┘  │
│  Pagination: [ < Prev ] Page 1 of 14 [ Next > ]              │  Client Notes: "Candidate has 6 yrs Spring Boot exp."   │
└──────────────────────────────────────────────────────────────┴─────────────────────────────────────────────────────────┘
```

---

### 4.5 Groq AI Interview Intake & Application Pipeline (`/applications`)

Powered by **Groq LLaMA 3.3 70B**, this view turns messy candidate email invites into structured updates:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  AI INTERVIEW RESPONSE INBOX                                                                                           │
│  Active View: [ [⚡ Intake Studio]  [📊 Application Pipeline Events] ] • Filter Client: [ ABC Staffing ▾ ]             │
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  MULTI-INPUT INTAKE CHANNELS                                                                                           │
│  [ 📝 Paste Raw Email Text ]  [ ✉ Upload .eml File ]  [ 📄 Upload PDF Invite ]  [ 🖼 Screenshot OCR Intake ]           │
│                                                                                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ From: recruiter@tcs.com                                                                                          │  │
│  │ Subject: Interview Scheduled - Java Developer - Rahul Kumar                                                      │  │
│  │ Hi Team, We have scheduled Round 1 Technical Interview for Rahul Kumar on 2026-08-26 at 10:00 AM for Java at TCS. │  │
│  └──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│  Quick 1-Click Samples: [ 📄 Interview Scheduled ] [ 💻 Round 2 Follow-up ] [ 🎉 Offer Letter ] [ 🚫 AWS Promo ]       │
│  [ ⚡ Analyze with Groq LLaMA 3.3 ]                                                                                    │
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  AI EXTRACTION & 4-TIER SMART LINKING RESULT (HUMAN CONFIRMATION CARD)                                                 │
│                                                                                                                        │
│  🤖 Groq Classification: "interview_scheduled" (Confidence: 99.4%) • Decision: POSITIVE RECRUITMENT EMAIL              │
│                                                                                                                        │
│  Parsed Entities (Editable Before Save):                                                                               │
│  - Candidate Name: [ Rahul Kumar             ]    - Hiring Company: [ TCS                    ]                         │
│  - Role / Designation: [ Senior Java Developer ]    - Interview Date: [ 2026-08-26 10:00 AM   ]                         │
│  - Interview Stage: [ Round 1 Technical      ]    - Pipeline Status: [ Shortlisted          ▾ ]                         │
│                                                                                                                        │
│  🔗 Smart Resume Linking:                                                                                              │
│  ✓ Matched Priority 2: "Rahul Kumar" + "TCS" ➔ Linked to Resume [ RES101 - Rahul_Kumar_TCS.pdf ]                      │
│  [ 🔄 Change Linked Resume ]                                                                                           │
│                                                                                                                        │
│  [ ✓ Confirm & Advance Candidate Pipeline ]   [ ✕ Dismiss / Mark Spam ]                                                │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

#### 4-Tier Smart Resume Linking Architecture:
1. **Tier 1 (Highest)**: Direct Resume Tag Match (`RES101`, `RES205`).
2. **Tier 2**: Exact Candidate Name + Hiring Company match.
3. **Tier 3**: Exact Candidate Name + Role Designation match.
4. **Tier 4 (Fallback)**: Create pipeline record with unlinked resume indicator (`resume_id = null`), allowing manual 1-click binding later.

---

### 4.6 Real-Time Role-Based Chat & Document Sharing (`/chats`)

Integrated WebSocket messaging for recruiter-to-client communication:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  LIVE CHAT CANVAS                                                                                                      │
├──────────────────────────────────────────────┬─────────────────────────────────────────────────────────────────────────┤
│  CHAT ROOMS (SERVICE CLIENTS)                │  CONVERSATION STREAM: ABC Staffing Workspace                            │
│                                              │  Participants: Harish (Recruiter), John (ABC Staffing Lead) • 🟢 Online │
│  ┌────────────────────────────────────────┐  ├─────────────────────────────────────────────────────────────────────────┤
│  │ 🏢 ABC Staffing                11:24 AM│  │ [10:30 AM] John (ABC Staffing):                                        │
│  │ Harish: Shared resume RES101...    [2] │  │ Hi Harish, do we have any Java candidates for the TCS opening?       │
│  ├────────────────────────────────────────┤  │                                                                         │
│  │ 🏢 Talent Hub Global           Yesterday│ │ [10:32 AM] Harish (Recruiter):                                        │
│  │ Vikram: Interview scheduled...         │  │ Yes John! I just ingested Rahul Kumar's profile. Attaching resume below:│
│  ├────────────────────────────────────────┤  │                                                                         │
│  │ 🏢 NextHire Logistics            Monday│  │ ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ Sneha: Offer letter received           │  │ │ 📄 Rahul_Kumar_TCS_Java.pdf (142 KB)                                │ │
│  └────────────────────────────────────────┘  │ │ │ Resume Tag: RES101 • Status: Shortlisted                          │ │
│                                              │ │ │ [ 👁 Inline Preview ]  [ ⬇ Download File ]                        │ │
│                                              │ │ └─────────────────────────────────────────────────────────────────────┘ │
│                                              │ │                                                                         │
│                                              │ │ [10:35 AM] John (ABC Staffing):                                        │
│                                              │ │ Looks great. Please schedule Round 1. ✓✓ Read 10:36 AM                 │
│                                              │ ├─────────────────────────────────────────────────────────────────────────┤
│                                              │ │ ✍️ John is typing...                                                   │
│                                              │ │ [ 📎 Attach File ] [ 📄 Share Candidate Resume ]                        │
│                                              │ │ [ Type a message to ABC Staffing...                                🚀 ] │
│                                              │ └─────────────────────────────────────────────────────────────────────────┘
```

---

### 4.7 Job Openings & Requirements Board (`/requirements`)

Task management matrix for open client requisitions:
- **Tabs**: Active Jobs (`active`), Completed History (`done`), Archived Jobs (`archived`).
- **Priority Indicators**: High (`#EF4444`), Medium (`#F97316`), Low (`#2563EB`).
- **Actions**: Create Requirement, Assign Recruiter, Edit Details, Mark as Done, Reopen, Archive, Safe Delete.

---

### 4.8 Service Client Management (`/clients`)

- **Card-Based & Table Views**: Total resumes ingested, applications submitted, assigned recruiters (Lead + Members).
- **Actions**: Create Client, Assign/Unassign Recruiters, Toggle Status (Active / Inactive), Archive, Export Data.

---

### 4.9 Sub-Admin Delegation Center (`/sub-admins`)

*Super Admin exclusive area*:
- Assign delegated Service Clients and Recruiters to Sub-Admins.
- Scoped operational boundaries prevent cross-organization visibility.

---

### 4.10 Analytics, Telemetry & Export Hub (`/reports`)

- **Multi-Tab Excel Export (`.xlsx`)**: Client breakdowns, candidate logs, daily quotas.
- **PDF Executive Summary**: Branded presentation with KPI graphics.
- **Lifecycle CSV Exports**: Active Clients, Archived Clients, Inactive Staff, Completed Targets.

---

## 5. Component Library & Interaction Design

### 5.1 Reusable UI Primitives

```
frontend/src/components/ui/
├── Avatar.jsx            -> High-contrast name-based initials with online status dot
├── BrandedLoader.jsx     -> ApplyFlow geometric brand loader with smooth rotation
├── Button.jsx            -> 6 variants (primary, secondary, outline, ghost, danger, success)
├── Card.jsx              -> Surface cards with elevation tokens
├── ChartSkeleton.jsx     -> Shimmer loading state for async visual charts
├── CommandPalette.jsx    -> Global ⌘K search and quick-jump menu
├── DateFilter.jsx        -> Quick presets (Today, Yesterday, Week, Month) + DatePicker
├── Dropdown.jsx          -> Accessible keyboard-navigable popovers
├── EmptyState.jsx        -> Illustrated state for zero results
├── ErrorBoundary.jsx     -> Graceful React error capture with reload trigger
├── Input.jsx             -> Form text field with floating labels and icon slots
├── KPICard.jsx           -> Metric cards with percentage trends and color themes
├── Modal.jsx             -> Framer-motion backdrop dialog with focus trap
├── NotificationItem.jsx  -> Bell alert rows with unread indicator
├── ProgressRing.jsx      -> SVG circular progress indicator supporting >100%
├── SearchBar.jsx         -> Debounced text search with clear button
├── Select.jsx            -> Styled select dropdown
├── StatusBadge.jsx       -> Rounded badges (Applied, Shortlisted, Interview, Offer, Rejected)
├── Table.jsx             -> High-density sortable, paginated data grid
├── Tabs.jsx              -> Pill and underline tab switchers
├── Toast.jsx             -> Context-driven push toast notification engine
└── UploadDropzone.jsx    -> Drag-and-drop batch file staging component
```

### 5.2 Micro-Interactions & Feedback Rules

1. **Active Nav Indicator**: Floating spring pill (`layoutId="active-sidebar-pill"`, `stiffness: 500`, `damping: 38`).
2. **Batch Upload Success**: Multi-colored celebration confetti burst (`canvas-confetti`).
3. **Live Attendance Timer**: Monospace ticker with pulsing green active status light.
4. **Command Palette (`⌘K`)**: Instant modal trigger with arrow-key navigation and backdrop blur.
5. **Real-Time WebSockets**: Live typing indicator with 3-dot bounce animation and auto-scroll to bottom.

---

## 6. Responsive Breakpoint & Adaptability Matrix

| Breakpoint | Target Screen Width | Navigation Behavior | Table / Card Strategy | Split-Screen Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **Desktop XL** | $\ge 1440\text{px}$ | Persistent 280px Floating Sidebar | Full multi-column data tables | Side-by-side (40% list / 60% viewer) |
| **Desktop L** | $1024\text{px} - 1439\text{px}$ | Persistent 260px Sidebar | Condensed column tables | Side-by-side (45% list / 55% viewer) |
| **Tablet** | $768\text{px} - 1023\text{px}$ | Hamburger Slide-out Drawer | Responsive scrollable table | Stacked view (Tap candidate opens modal) |
| **Mobile** | $375\text{px} - 767\text{px}$ | Full-screen Slide-out Drawer | Converts table rows to Touch Cards | Full-screen single view with Back button |

---

## 7. Accessibility (a11y) & Performance Engineering

- **Color Contrast**: All text elements meet **WCAG 2.1 AA standards** (minimum contrast ratio $\ge 4.5:1$ for body text, $\ge 3:1$ for headers).
- **Keyboard Navigation**:
  - `⌘K` / `Ctrl+K`: Opens Global Command Palette.
  - `Esc`: Closes any open Modal, Drawer, or Palette.
  - `Tab` / `Shift+Tab`: Full focus trapping within Modals.
- **Route Code Splitting**: All page components use `React.lazy()` with `Suspense` and `BrandedLoader` fallbacks.
- **Chart Deferral**: Charts are lazy-loaded via subcomponents (`AdminCharts`, `EmployeeCharts`, `ClientCharts`) to guarantee $< 150\text{ms}$ Time-to-Interactive (TTI).

---

## 8. Design Validation Checklist

- [x] Strict separation of Service Clients vs Hiring Companies.
- [x] Role-based permissions strictly enforced across all 4 roles.
- [x] Super Admin prohibited from direct resume uploading to maintain audit purity.
- [x] Daily target quota formulas strictly mapped to Applications Submitted.
- [x] 0-50% Red, 51-99% Orange, 100%+ Green visual target thresholds.
- [x] Groq LLaMA 3.3 AI Email Intake with 4-tier resume linking.
- [x] WebSocket live chat with inline candidate resume attachment.
- [x] Shift check-in/check-out session timer.
- [x] Multi-format report exports (Excel, PDF, CSV).
- [x] Mobile and tablet responsive drawer and touch card fallbacks.

---
*Created and maintained by the ApplyFlow Core Product & Engineering Team.*
