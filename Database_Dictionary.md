# ApplyFlow — Complete Database Dictionary & Schema Specification

> **Database Engines**: PostgreSQL 15+ (Production / Neon) / SQLite 3 (Local Development)  
> **ORM Framework**: SQLAlchemy 2.0 (Declarative Base, AsyncPG driver)  
> **Migration Engine**: Alembic (Sequential revision migrations)  
> **Primary Key Standard**: `UUID` (128-bit UUIDv4 across all core entities)

---

## 1. Schema Overview & Relational Architecture

The ApplyFlow database schema is normalized around multi-tenant customer isolation, candidate deduplication, auditability, and real-time operational telemetry.

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│      users      │◄──────┤employee_clients ├──────►│     clients     │
└────────┬────────┘       └─────────────────┘       └────────┬────────┘
         │                                                   │
         │ (1..N)                                            │ (1..N)
         ▼                                                   ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     resumes     │◄──────┤  requirements   │◄──────┤   chat_rooms    │
└────────┬────────┘       └────────┬────────┘       └────────┬────────┘
         │                         │                         │
         │ (1..1)                  │ (1..N)                  │ (1..N)
         ▼                         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  applications   │◄──────┤application_event│       │  chat_messages  │
└────────┬────────┘       └─────────────────┘       └─────────────────┘
         │
         ▼
┌─────────────────┐
│  email_intake   │
└─────────────────┘
```

---

## 2. Table Specifications

### 2.1 `users`
- **Purpose**: System accounts, authentication credentials, role definitions, and organizational status.
- **Table Name**: `users`

| Column | Data Type | Nullable | Default | Constraints & Indexes | Description & Business Rules |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `id` | `UUID` | **NO** | `uuid.uuid4` | **PRIMARY KEY** | Unique internal identifier for user. |
| `name` | `VARCHAR(100)` | **NO** | — | — | Full name of user (Recruiter, Admin, Client Contact). |
| `email` | `VARCHAR(255)` | **NO** | — | `UNIQUE`, `INDEX (ix_users_email)` | Corporate login email address. Always lowercased on insertion. |
| `phone` | `VARCHAR(50)` | YES | `NULL` | — | Contact telephone number. |
| `password_hash`| `VARCHAR(255)` | **NO** | — | — | 60-character bcrypt salted password hash. |
| `role` | `VARCHAR(20)` | **NO** | — | `INDEX (ix_users_role_active)` | System role: `"admin"`, `"sub_admin"`, `"employee"`, `"client"`. |
| `status` | `VARCHAR(20)` | **NO** | `'active'` | — | Account status: `"active"`, `"inactive"`, `"archived"`. |
| `client_id` | `UUID` | YES | `NULL` | `FOREIGN KEY (clients.id)` | For `role="client"`, binds user to exactly one Service Client. |
| `managed_by` | `UUID` | YES | `NULL` | `FOREIGN KEY (users.id)` | Assigns supervising Admin / Sub-Admin. |
| `is_active` | `BOOLEAN` | **NO** | `true` | `INDEX (ix_users_role_active)` | Login gating flag. `false` prevents login even with valid password. |
| `created_at` | `TIMESTAMP(TZ)`| **NO** | `NOW()` | — | Account creation timestamp. |
| `updated_at` | `TIMESTAMP(TZ)`| **NO** | `NOW()` | — | Last modification timestamp. |

---

### 2.2 `clients`
- **Purpose**: Service Client companies (staffing customers who contract ApplyFlow).
- **Table Name**: `clients`

| Column | Data Type | Nullable | Default | Constraints & Indexes | Description & Business Rules |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `id` | `UUID` | **NO** | `uuid.uuid4` | **PRIMARY KEY** | Unique customer identifier. |
| `company_name` | `VARCHAR(200)` | **NO** | — | `UNIQUE`, `INDEX (ix_clients_name)` | Official corporate name (e.g. *ABC Staffing*). |
| `contact_person`| `VARCHAR(100)` | YES | `NULL` | — | Primary client liaison. |
| `email` | `VARCHAR(255)` | YES | `NULL` | — | Primary billing/contact email. |
| `phone` | `VARCHAR(50)` | YES | `NULL` | — | Customer support/direct phone. |
| `status` | `VARCHAR(20)` | **NO** | `'active'` | — | Lifecycle state: `"active"`, `"inactive"`, `"archived"`. |
| `logo_url` | `VARCHAR(500)` | YES | `NULL` | — | CDN or S3 URL for company logo icon. |
| `drive_folder_id`| `VARCHAR(255)`| YES | `NULL` | — | Google Drive folder ID for client's resumes. |
| `managed_by` | `UUID` | YES | `NULL` | `FOREIGN KEY (users.id)` | Supervising Sub-Admin ID. |
| `is_active` | `BOOLEAN` | **NO** | `true` | — | Quick activation status. |
| `deactivated_at`| `TIMESTAMP(TZ)`| YES | `NULL` | — | Timestamp when client was marked inactive. |
| `archived_at` | `TIMESTAMP(TZ)`| YES | `NULL` | — | Timestamp when client was moved to archives. |
| `created_at` | `TIMESTAMP(TZ)`| **NO** | `NOW()` | — | Client creation timestamp. |

---

### 2.3 `employee_clients`
- **Purpose**: Many-to-many junction assigning recruiters (`users`) to Service Clients (`clients`).
- **Table Name**: `employee_clients`

| Column | Data Type | Nullable | Default | Constraints & Indexes | Description & Business Rules |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `id` | `UUID` | **NO** | `uuid.uuid4` | **PRIMARY KEY** | Unique assignment record ID. |
| `employee_id` | `UUID` | **NO** | — | `FOREIGN KEY (users.id)`, `INDEX` | Recruiter user ID. |
| `client_id` | `UUID` | **NO** | — | `FOREIGN KEY (clients.id)`, `INDEX`| Service Client ID. |
| `is_primary` | `BOOLEAN` | **NO** | `false` | — | Designates lead recruiter for the client. |
| `active` | `BOOLEAN` | **NO** | `true` | `INDEX (ix_emp_client_active)` | Active assignment flag. |
| `assigned_at` | `TIMESTAMP(TZ)`| **NO** | `NOW()` | — | When assignment was established. |
| `assigned_by` | `UUID` | YES | `NULL` | `FOREIGN KEY (users.id)` | Admin who created assignment. |

---

### 2.4 `sub_admin_assignments`
- **Purpose**: Super Admin delegation matrix assigning Service Clients and Recruiters to Sub-Admins.
- **Table Name**: `sub_admin_assignments`

| Column | Data Type | Nullable | Default | Constraints & Indexes | Description & Business Rules |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `id` | `UUID` | **NO** | `uuid.uuid4` | **PRIMARY KEY** | Unique assignment record ID. |
| `sub_admin_id` | `UUID` | **NO** | — | `FOREIGN KEY (users.id)`, `INDEX` | Sub-Admin user ID. |
| `employee_id` | `UUID` | YES | `NULL` | `FOREIGN KEY (users.id)`, `INDEX` | Delegated recruiter ID. |
| `client_id` | `UUID` | YES | `NULL` | `FOREIGN KEY (clients.id)`, `INDEX`| Delegated Service Client ID. |
| `active` | `BOOLEAN` | **NO** | `true` | — | Delegation state. |
| `assigned_at` | `TIMESTAMP(TZ)`| **NO** | `NOW()` | — | Timestamp of delegation. |

---

### 2.5 `resumes`
- **Purpose**: Candidate profiles ingested into Service Clients, file storage references, and metadata.
- **Table Name**: `resumes`

| Column | Data Type | Nullable | Default | Constraints & Indexes | Description & Business Rules |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `id` | `UUID` | **NO** | `uuid.uuid4` | **PRIMARY KEY** | Unique resume record ID. |
| `display_seq` | `INTEGER` | YES | `NULL` | — | Sequence integer for generating user-facing `RES1001` tags. |
| `candidate_name`| `VARCHAR(200)` | **NO** | — | `INDEX` | Candidate's extracted full name. |
| `company` | `VARCHAR(100)` | **NO** | — | `INDEX (ix_resumes_client_comp)`| Target Hiring Company (e.g. *TCS*, *Google*). |
| `role` | `VARCHAR(200)` | **NO** | — | `INDEX (ix_resumes_role)` | Job role title (e.g. *Senior Java Developer*). |
| `resume_id_tag` | `VARCHAR(100)` | YES | `NULL` | `INDEX (ix_resumes_tag)` | Explicit tag parsed from filename (e.g. `RES101`). |
| `requirement_id`| `UUID` | YES | `NULL` | `FOREIGN KEY (requirements.id)`| Optional linked job requisition. |
| `client_id` | `UUID` | **NO** | — | `FOREIGN KEY (clients.id)`, `INDEX`| Owning Service Client ID. |
| `uploaded_by` | `UUID` | **NO** | — | `FOREIGN KEY (users.id)`, `INDEX` | Ingesting recruiter user ID. |
| `drive_file_id` | `VARCHAR(255)` | YES | `NULL` | — | Google Drive file ID or local storage ID (`file_...`). |
| `original_filename`| `VARCHAR(500)`| **NO** | — | — | Raw uploaded filename. |
| `resume_date` | `DATE` | YES | `NULL` | `INDEX (ix_resumes_client_date)`| Effective upload date for quota calculation. |
| `client_notes` | `TEXT` | YES | `NULL` | — | Recruiter evaluation notes. |
| `is_note_shared`| `BOOLEAN` | **NO** | `false` | — | Visibility flag for Client Portal users. |
| `upload_date` | `TIMESTAMP(TZ)`| **NO** | `NOW()` | — | Exact server timestamp of ingestion. |

---

### 2.6 `requirements`
- **Purpose**: Client job requisitions and open hiring requirements.
- **Table Name**: `requirements`

| Column | Data Type | Nullable | Default | Constraints & Indexes | Description & Business Rules |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `id` | `UUID` | **NO** | `uuid.uuid4` | **PRIMARY KEY** | Unique requirement ID. |
| `client_id` | `UUID` | **NO** | — | `FOREIGN KEY (clients.id)`, `INDEX`| Owning Service Client ID. |
| `company` | `VARCHAR(100)` | **NO** | — | `INDEX` | Target Hiring Company. |
| `role` | `VARCHAR(200)` | **NO** | — | `INDEX` | Target job title. |
| `job_title` | `VARCHAR(200)` | YES | `NULL` | — | Canonical title alias. |
| `role_code` | `VARCHAR(50)` | **NO** | — | `INDEX` | Unique job requisition code (e.g. `TCS-JAVA-01`). |
| `job_url` | `VARCHAR(500)` | YES | `NULL` | — | External careers portal URL. |
| `priority` | `VARCHAR(20)` | **NO** | `'Medium'` | — | Priority: `"High"`, `"Medium"`, `"Low"`. |
| `notes` | `TEXT` | YES | `NULL` | — | Recruiter sourcing instructions. |
| `status` | `VARCHAR(20)` | **NO** | `'active'` | — | Status: `"active"`, `"done"`, `"archived"`, `"closed"`. |
| `assignment_type`| `VARCHAR(20)`| **NO** | `'all'` | — | Assignment scope: `"all"` (All client recruiters) or `"individual"`. |
| `assigned_employee_id`| `UUID` | YES | `NULL` | `FOREIGN KEY (users.id)` | Specific assigned recruiter ID if individual. |
| `created_by` | `UUID` | YES | `NULL` | `FOREIGN KEY (users.id)` | Creating Admin / Recruiter ID. |
| `completed_by` | `UUID` | YES | `NULL` | `FOREIGN KEY (users.id)` | User who marked requisition done. |
| `created_at` | `TIMESTAMP(TZ)`| **NO** | `NOW()` | — | Requisition creation timestamp. |
| `completed_at` | `TIMESTAMP(TZ)`| YES | `NULL` | — | Completion timestamp. |

---

### 2.7 `applications`
- **Purpose**: Candidate hiring pipeline progression for a Service Client requisition.
- **Table Name**: `applications`

| Column | Data Type | Nullable | Default | Constraints & Indexes | Description & Business Rules |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `id` | `UUID` | **NO** | `uuid.uuid4` | **PRIMARY KEY** | Unique application pipeline ID. |
| `resume_id` | `UUID` | YES | `NULL` | `FOREIGN KEY (resumes.id)`, `INDEX`| Linked resume ID (Nullable for unlinked AI events). |
| `candidate_name`| `VARCHAR(200)` | YES | `NULL` | `INDEX` | Fallback candidate name if unlinked. |
| `company` | `VARCHAR(100)` | YES | `NULL` | `INDEX` | Fallback company name if unlinked. |
| `role` | `VARCHAR(200)` | YES | `NULL` | `INDEX` | Fallback role title if unlinked. |
| `requirement_id`| `UUID` | YES | `NULL` | `FOREIGN KEY (requirements.id)`, `INDEX`| Associated job requisition. |
| `employee_id` | `UUID` | **NO** | — | `FOREIGN KEY (users.id)`, `INDEX (ix_apps_emp_applied)` | Managing recruiter ID. |
| `client_id` | `UUID` | YES | `NULL` | `FOREIGN KEY (clients.id)`, `INDEX (ix_apps_client_applied)`| Service Client ID. |
| `status` | `VARCHAR(50)` | **NO** | `'Submitted'` | `INDEX (ix_apps_status_applied)` | Pipeline status (Submitted, Shortlisted, Round 1, Offer, etc.). |
| `current_round` | `VARCHAR(100)` | YES | `'Initial Application'` | — | Detailed round name. |
| `interview_date`| `TIMESTAMP(TZ)`| YES | `NULL` | — | Scheduled interview date and time. |
| `confidence` | `INTEGER` | YES | `95` | — | AI extraction confidence score. |
| `last_email_snippet`| `TEXT` | YES | `NULL` | — | Raw snippet of latest email update. |
| `is_ai_processed`| `BOOLEAN` | **NO** | `false` | — | True if created or advanced by Groq AI Inbox. |
| `applied_date` | `TIMESTAMP(TZ)`| **NO** | `NOW()` | `INDEX (ix_apps_emp_applied)` | Submission date used in quota engine. |
| `updated_at` | `TIMESTAMP(TZ)`| **NO** | `NOW()` | — | Last status change timestamp. |

---

### 2.8 `application_events`
- **Purpose**: Immutable chronological audit log of all candidate interview rounds and updates.
- **Table Name**: `application_events`

| Column | Data Type | Nullable | Default | Constraints & Indexes | Description & Business Rules |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `id` | `UUID` | **NO** | `uuid.uuid4` | **PRIMARY KEY** | Unique event ID. |
| `application_id`| `UUID` | **NO** | — | `FOREIGN KEY (applications.id) ON DELETE CASCADE`, `INDEX` | Owning application ID. |
| `event_type` | `VARCHAR(100)` | **NO** | — | — | Event classification (Submitted, Round 1, Offer, etc.). |
| `round_name` | `VARCHAR(100)` | YES | `NULL` | — | Human-readable round title. |
| `event_date` | `TIMESTAMP(TZ)`| YES | `NULL` | — | Effective timestamp of event. |
| `email_id` | `UUID` | YES | `NULL` | `FOREIGN KEY (email_intake.id)`| Linked raw email intake record. |
| `raw_email` | `TEXT` | YES | `NULL` | — | Raw body snippet triggering event. |
| `ai_json` | `JSON` | YES | `NULL` | — | Groq AI extraction JSON payload. |
| `confidence` | `INTEGER` | **NO** | `90` | — | Extraction confidence. |
| `interview_date`| `TIMESTAMP(TZ)`| YES | `NULL` | — | Interview schedule if extracted. |
| `created_by` | `UUID` | YES | `NULL` | `FOREIGN KEY (users.id)` | User who confirmed event. |
| `created_at` | `TIMESTAMP(TZ)`| **NO** | `NOW()` | `INDEX` | Audit record timestamp. |

---

### 2.9 `email_intake`
- **Purpose**: Raw ingested recruiter emails and extraction records.
- **Table Name**: `email_intake`

| Column | Data Type | Nullable | Default | Constraints & Indexes | Description & Business Rules |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `id` | `UUID` | **NO** | `uuid.uuid4` | **PRIMARY KEY** | Unique intake ID. |
| `uploaded_by` | `UUID` | **NO** | — | `FOREIGN KEY (users.id)`, `INDEX` | Recruiter who submitted email. |
| `client_id` | `UUID` | YES | `NULL` | `FOREIGN KEY (clients.id)`, `INDEX`| Target Service Client. |
| `original_text` | `TEXT` | **NO** | — | — | Complete raw email body text. |
| `source_type` | `VARCHAR(50)` | **NO** | `'paste'` | — | Source channel: `"paste"`, `"eml"`, `"pdf"`, `"image"`. |
| `confidence` | `INTEGER` | **NO** | `95` | — | Extraction score. |
| `processed` | `BOOLEAN` | **NO** | `true` | — | True if confirmed and applied. |
| `created_at` | `TIMESTAMP(TZ)`| **NO** | `NOW()` | `INDEX` | Ingestion timestamp. |

---

### 2.10 `targets`
- **Purpose**: Daily submission quotas assigned by Admins to Recruiters per Service Client.
- **Table Name**: `targets`

| Column | Data Type | Nullable | Default | Constraints & Indexes | Description & Business Rules |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `id` | `UUID` | **NO** | `uuid.uuid4` | **PRIMARY KEY** | Unique target ID. |
| `employee_id` | `UUID` | **NO** | — | `FOREIGN KEY (users.id)`, `INDEX (ix_targets_emp_status)` | Recruiter user ID. |
| `client_id` | `UUID` | **NO** | — | `FOREIGN KEY (clients.id)`, `INDEX (ix_targets_client_status)`| Service Client ID. |
| `daily_target` | `INTEGER` | **NO** | — | — | Target submission count per day. |
| `status` | `VARCHAR(20)` | **NO** | `'active'` | `INDEX` | Status: `"active"`, `"paused"`, `"ended"`. |
| `effective_date`| `DATE` | **NO** | `CURRENT_DATE`| `INDEX (ix_targets_effective_date)`, `UNIQUE(emp, client, date)` | Start date for quota enforcement. |
| `created_at` | `TIMESTAMP(TZ)`| **NO** | `NOW()` | `INDEX` | Record timestamp. |

---

### 2.11 `attendance`
- **Purpose**: Shift time tracking and workday check-in/check-out records.
- **Table Name**: `attendance`

| Column | Data Type | Nullable | Default | Constraints & Indexes | Description & Business Rules |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `id` | `UUID` | **NO** | `uuid.uuid4` | **PRIMARY KEY** | Unique session ID. |
| `employee_id` | `UUID` | **NO** | — | `FOREIGN KEY (users.id)`, `INDEX (ix_attendance_emp_date)` | Recruiter user ID. |
| `work_date` | `DATE` | **NO** | `CURRENT_DATE`| `INDEX` | Calendar workday. |
| `check_in` | `TIMESTAMP(TZ)`| **NO** | `NOW()` | — | Exact check-in timestamp. |
| `check_out` | `TIMESTAMP(TZ)`| YES | `NULL` | — | Exact check-out timestamp. |
| `total_hours` | `VARCHAR(50)` | YES | `NULL` | — | Calculated duration string (e.g. `"8h 15m"`). |

---

### 2.12 `chat_rooms`, `chat_messages`, `chat_reads`
- **Purpose**: Real-time customer communication and cursor read tracking.

#### `chat_rooms`:
| Column | Data Type | Nullable | Default | Constraints & Indexes |
| :--- | :--- | :---: | :---: | :--- |
| `id` | `UUID` | **NO** | `uuid.uuid4` | **PRIMARY KEY** |
| `client_id` | `UUID` | **NO** | — | `FOREIGN KEY (clients.id)`, `UNIQUE` |
| `status` | `VARCHAR(20)` | **NO** | `'active'` | `"active"`, `"read_only"`, `"archived"` |
| `created_at` | `TIMESTAMP(TZ)`| **NO** | `NOW()` | — |

#### `chat_messages`:
| Column | Data Type | Nullable | Default | Constraints & Indexes |
| :--- | :--- | :---: | :---: | :--- |
| `id` | `UUID` | **NO** | `uuid.uuid4` | **PRIMARY KEY** |
| `room_id` | `UUID` | **NO** | — | `FOREIGN KEY (chat_rooms.id)`, `INDEX (ix_chat_messages_room_created)` |
| `sender_id` | `UUID` | **NO** | — | `FOREIGN KEY (users.id)`, `INDEX` |
| `message` | `TEXT` | **NO** | `''` | Body text of message |
| `attachment_type` | `VARCHAR(20)`| YES | `NULL` | `"resume"`, `"pdf"`, `"file"` |
| `attachment_reference`| `VARCHAR(500)`| YES | `NULL` | Resume UUID or Drive file ID |
| `created_at` | `TIMESTAMP(TZ)`| **NO** | `NOW()` | `INDEX` |

#### `chat_reads`:
| Column | Data Type | Nullable | Default | Constraints & Indexes |
| :--- | :--- | :---: | :---: | :--- |
| `id` | `UUID` | **NO** | `uuid.uuid4` | **PRIMARY KEY** |
| `user_id` | `UUID` | **NO** | — | `FOREIGN KEY (users.id)`, `UNIQUE(user, room)` |
| `room_id` | `UUID` | **NO** | — | `FOREIGN KEY (chat_rooms.id)` |
| `last_read_message_id`| `UUID` | YES | `NULL` | `FOREIGN KEY (chat_messages.id)` |
| `last_read_at` | `TIMESTAMP(TZ)`| **NO** | `NOW()` | — |

---

### 2.13 `notifications`
- **Purpose**: Multi-role operational alert feed.
- **Table Name**: `notifications`

| Column | Data Type | Nullable | Default | Constraints & Indexes | Description & Business Rules |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `id` | `UUID` | **NO** | `uuid.uuid4` | **PRIMARY KEY** | Unique notification ID. |
| `user_id` | `UUID` | **NO** | — | `FOREIGN KEY (users.id)`, `INDEX (ix_notifications_user_read_created)` | Recipient user ID. |
| `title` | `VARCHAR(200)` | **NO** | — | — | Short alert headline. |
| `message` | `VARCHAR(500)` | **NO** | — | — | Detailed notification description. |
| `type` | `VARCHAR(50)` | **NO** | `'info'` | — | Category: `"upload_completed"`, `"application"`, `"target_achieved"`. |
| `is_read` | `BOOLEAN` | **NO** | `false` | `INDEX` | Read state flag. |
| `created_at` | `TIMESTAMP(TZ)`| **NO** | `NOW()` | `INDEX` | Creation timestamp. |

---

### 2.14 `activity_logs`
- **Purpose**: System-wide compliance and security audit trail.
- **Table Name**: `activity_logs`

| Column | Data Type | Nullable | Default | Constraints & Indexes | Description & Business Rules |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `id` | `UUID` | **NO** | `uuid.uuid4` | **PRIMARY KEY** | Unique audit record ID. |
| `user_id` | `UUID` | **NO** | — | `FOREIGN KEY (users.id)`, `INDEX` | Acting user ID. |
| `action` | `VARCHAR(50)` | **NO** | — | `INDEX` | Action key (`"login"`, `"resume_uploaded"`, `"target_set"`). |
| `details` | `JSON` | YES | `NULL` | — | Structured contextual payload. |
| `created_at` | `TIMESTAMP(TZ)`| **NO** | `NOW()` | — | Immutable audit timestamp. |
