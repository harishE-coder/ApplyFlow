# ApplyFlow

<div align="center">

<h3>AI-Powered Recruitment Workspace for Resume Management, Client Collaboration, and Interview Tracking</h3>

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React_18-61DAFB.svg?logo=react)](https://react.dev)
[![Vite](https://img.shields.io/badge/Bundler-Vite_6-646CFF.svg?logo=vite)](https://vitejs.dev)
[![Tailwind CSS](https://img.shields.io/badge/Styling-Tailwind_CSS_v4-38B2AC.svg?logo=tailwind-css)](https://tailwindcss.com)
[![Groq AI](https://img.shields.io/badge/AI-Groq_LLaMA_3.3_70B-F55036.svg)](https://groq.com)

</div>

---

## 📖 Overview

**ApplyFlow** is a modern recruitment workspace built specifically for recruitment agencies, staffing firms, and Talent Operations teams.

Traditional ATS platforms often confuse hiring clients with target employers. ApplyFlow implements a clean, real-world business model that separates:
1. **Service Clients (Our Customers)**: Staffing customers (e.g., *ABC Staffing*, *Talent Hub*) who contract our agency.
2. **Hiring Companies**: End-client employers (e.g., *Amazon*, *Google*, *TCS*, *Infosys*).
3. **Recruiters (Employees)**: Dedicated talent specialists assigned to specific Service Clients.
4. **Candidates & Resumes**: Ingested talent profiles with automated tagging and deduplication.
5. **Applications & Pipelines**: Live candidate progress across submission, interview rounds, offers, and join dates.

From bulk PDF resume ingestion to **Groq-powered AI email interview parsing**, ApplyFlow streamlines the entire recruitment lifecycle into a unified, real-time operating system.

---

## ✨ Core Features

### 📄 Resume Management
- **Bulk PDF Upload**: Ingest 1 to 100+ resumes in a single batch.
- **Cloud Storage**: Secure Google Drive integration via Google Apps Script Web App.
- **Smart Filename Tokenizer**: Automatically parses candidate metadata from standard filenames:
  ```text
  TCS_JavaDeveloper_RES101.pdf
  ├── Company: TCS
  ├── Role: Java Developer
  └── Resume ID Tag: RES101
  ```
- **Pre-Commit Duplicate Check**: Identifies duplicates before storage commits.
- **Protected PDF Streaming**: Zero-leakage inline preview and raw PDF downloads.
- **Instant Candidate Search**: Multi-parameter search by client, company, role designation, and resume tag.

---

### 🤖 AI Interview Intake (Powered by Groq LLaMA 3.3)
Turn messy interview invitation emails into structured candidate pipeline updates in seconds.
- **Multi-Input Intake**: Paste raw email text, upload `.eml` files, or upload interview invite screenshots (OCR).
- **Intelligent Classification**:
  - Automatically identifies positive interview invitations and round updates.
  - Automatically ignores newsletters, spam, and unrelated emails (`decision: "not_related"`).
- **Automated Extraction**: Extracts Candidate Name, Hiring Company, Role, Interview Date/Time, and Round Name.
- **4-Tier Smart Resume Linking**:
  1. *Priority 1*: Resume ID Tag (`RES101`).
  2. *Priority 2*: Candidate Name + Hiring Company.
  3. *Priority 3*: Candidate Name + Role Designation.
  4. *Priority 4*: Unmatched fallback (creates pipeline record with nullable resume ID).

---

### 🛡️ Role-Based Access Control (RBAC)
ApplyFlow enforces strict permission boundaries across four distinct roles:

| Role | Permissions & Responsibilities |
| :--- | :--- |
| **Super Admin** | Full platform authority, create clients/employees/sub-admins, set daily targets, view global company dashboards. *(Cannot upload resumes directly to preserve recruiter accountability).* |
| **Sub-Admin** | Delegated management over assigned service clients and recruiters without global visibility. |
| **Employee (Recruiter)** | Dedicated recruiter workspace, bulk resume uploads, Candidate Studio, AI intake, daily quota tracking, and client chat. |
| **Service Client** | Customer portal access to view only their assigned resumes, candidate interview pipeline, and recruiter chat. |

---

### 📊 Smart Real-Time Dashboards & Telemetry
- **Admin Command Center**: Global company overview with cascading filters (All Clients, Single Client, Employee, Date range), live target quotas, and attendance rosters.
- **Recruiter Workspace**:
  - Dynamic Daily Target Quota widget recalculating in real-time.
  - Today's Uploads counter vs. Applications Submitted counter.
  - Live progress donut ring supporting $>100\%$ over-achievement.
- **Client Portal**: Dedicated view with applied counts, interview stages, hiring companies, and chronological candidate activity timeline.

---

### 🎯 Targets & Quota Engine
Administrators assign daily submission targets per recruiter per client:
$$\text{Completion \%} = \left(\frac{\text{Applications Submitted}}{\text{Daily Target}}\right) \times 100$$
$$\text{Remaining} = \max(\text{Daily Target} - \text{Applications Submitted}, 0)$$
- Real-time color thresholds: **Red** ($0-50\%$), **Orange** ($51-99\%$), **Green** ($100\%+$).

---

### 💬 Real-Time Role-Based Chat
- Direct messaging between assigned Recruiters and Service Clients.
- Super Admin and Sub-Admin oversight.
- Real-time WebSocket broadcasting, typing indicators, read receipts, and unread badge counters.

---

### ⏰ Shift Attendance & Time Tracking
- One-click **Check In** and **Check Out** for recruiters.
- Active session tracking with live duration calculation.
- Admin Live Attendance Roster displaying present, working, and checked-out staff.

---

### 📑 Reports & Data Exports
- Multi-sheet Excel exports (`.xlsx`) with breakdown by client and recruiter.
- CSV data exports for active/archived clients, employees, and targets.
- Branded PDF recruitment summary reports.

---

## 🔄 Business Workflow

```
Recruiter (Employee)
       │
       ▼
Bulk Resume Upload (PDF)
       │
       ├───────────────────────────────┐
       ▼                               ▼
Google Drive Cloud Storage       Metadata & Application Ingestion
                                       │
       ┌───────────────────────────────┴───────────────────────────────┐
       ▼                                                               ▼
Client Portal Updated                                         Recruiter Dashboard & Quota Updated
       │
       ▼
Client/Employer Sends Interview Email
       │
       ▼
AI Interview Intake (Groq LLaMA 3.3)
       │
       ▼
Application Pipeline Advanced & Event Timeline Logged
```

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      React 18 Frontend                      │
│        (Vite + Tailwind CSS v4 + React Router v7)          │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTPS / WSS
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Backend API                     │
│               (Python 3.11+ / Uvicorn / JWT)                │
└───┬──────────────────────────┬──────────────────────────┬───┘
    │                          │                          │
    ▼                          ▼                          ▼
┌──────────────┐       ┌──────────────┐       ┌──────────────────────┐
│  PostgreSQL  │       │   Groq AI    │       │  Google Drive Cloud  │
│  or SQLite   │       │  (LLaMA 3.3) │       │ (Apps Script WebApp) │
└──────────────┘       └──────────────┘       └──────────────────────┘
```

---

## 🗄️ Database Schema

ApplyFlow utilizes SQLAlchemy 2.0 with the following core entities:

- `users`: Accounts, roles (`admin`, `sub_admin`, `employee`, `client`), and status.
- `clients`: Service client companies, primary contacts, and activation status.
- `employee_clients`: Many-to-many recruiter-to-client assignments.
- `sub_admin_assignments`: Delegations from Super Admin to Sub-Admins.
- `resumes`: Ingested candidate files, Google Drive references, and parsed tokens.
- `requirements`: Client job openings and designation codes.
- `applications`: Candidate pipeline records, interview stages, and notes.
- `application_events`: Chronological audit trail of interview progression.
- `targets`: Recruiter daily application goals.
- `attendance`: Recruiter shift check-ins and check-outs.
- `chat_rooms`, `chat_messages`, `chat_reads`: Real-time chat system.
- `notifications`: In-app event alerts.
- `activity_logs`: Audit trail for compliance and security.

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** & **npm**
- **Git**

### 1. Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/ApplyFlow.git
cd ApplyFlow
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Seed the database with demo accounts and initial data
python seed.py

# Start backend server
uvicorn app.main:app --reload --port 8000
```
Backend API will be accessible at: `http://localhost:8000`  
Interactive API Docs (Swagger): `http://localhost:8000/docs`

### 3. Frontend Setup
```bash
# In a new terminal window
cd frontend
npm install
npm run dev
```
Frontend Workspace will be accessible at: `http://localhost:5173`

---

## 🔑 Default Demo Accounts

The database seed script initializes the following pre-configured user accounts:

| Role | Email | Password | Assigned Scope |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@applyflow.com` | `admin123` | Global Platform Authority |
| **Sub-Admin** | `punith@applyflow.com` | `punith123` | Delegated to ABC Staffing & Harish |
| **Employee (Recruiter)** | `harish@applyflow.com` | `harish123` | Assigned to ABC Staffing & Talent Hub |
| **Employee 2** | `recruiter2@applyflow.com` | `recruiter123` | Assigned to NextHire |
| **Client** | `john@abcstaffing.com` | `client123` | ABC Staffing Customer Portal |
| **Client** | `sarah@talenthub.com` | `client123` | Talent Hub Customer Portal |

---

## ⚙️ Environment Variables

Configure these keys in `backend/.env`:

| Variable | Description | Example / Default |
| :--- | :--- | :--- |
| `USE_SQLITE` | Use SQLite for zero-config local development | `True` |
| `DATABASE_URL_OVERRIDE` | Database connection string | `sqlite+aiosqlite:///./applyflow.db` |
| `JWT_SECRET_KEY` | Cryptographic secret for signing JWTs | `your-secure-random-32-char-key` |
| `JWT_ALGORITHM` | Algorithm for JWT tokens | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES`| Access token lifetime | `60` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | `7` |
| `GROQ_API_KEY` | API Key for Groq LLaMA 3.3 AI Intake | `gsk_...` |
| `GOOGLE_APPS_SCRIPT_URL` | Google Apps Script Web App for Drive | `https://script.google.com/macros/s/.../exec` |
| `FRONTEND_URL` | Frontend origin for CORS policy | `http://localhost:5173` |

---

## 📱 Mobile & Responsive Support

ApplyFlow is fully responsive and optimized for:
- **Desktop** ($1440\text{px}+$): Multi-column dashboards, real-time split chat, table analytics.
- **Tablet** ($768\text{px} - 1024\text{px}$): Adaptive sidebar and collapsed stats overview.
- **Mobile** ($375\text{px} - 430\text{px}$): Touch-friendly navigation, modal upload workflows, responsive data cards.

---

## 🔒 Security

- **Dual JWT HTTP-Only Cookies**: Protected against XSS and token interception.
- **Zero IDOR Vulnerabilities**: Multi-tenant customer isolation enforced on all candidate routes.
- **Parameterized Queries**: SQLAlchemy ORM protection against SQL Injection.
- **Upload Restrictions**: Admin cannot upload directly; file type validation strictly enforced.

---

## 🗺️ Roadmap

- [x] v1.1 MVP: AI Email Intake, Daily Target Quota Engine, Role-Based Chat, Attendance.
- [ ] v1.2: Direct Gmail and Microsoft Outlook OAuth inbox listener.
- [ ] v1.3: Calendar synchronization (Google Calendar / Outlook) for interview scheduling.
- [ ] v1.4: Resume OCR parsing for legacy scanned image resumes.
- [ ] v1.5: Advanced recruitment analytics & custom KPI report builder.

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.

---

<div align="center">

Built with ❤️ by the **ApplyFlow Careers** Team.

</div>
