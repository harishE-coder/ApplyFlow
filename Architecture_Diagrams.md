# ApplyFlow ATS — Complete Architecture Diagrams (Mermaid)

> **Specification Version**: 1.2.0  
> **Visual Standards**: GitHub Flavored Mermaid Diagrams covering topologies, relational ERDs, state machines, and sequence workflows

---

## 1. System Topology & Infrastructure

```mermaid
flowchart TB
    subgraph ClientTier["Client Tier (Frontend Workspace)"]
        Browser["React 18 Workspace\n(Vite 6, Tailwind CSS v4)"]
        SWRStore["SWR In-Memory Cache\n& In-Flight Deduplicator"]
        WSSub["WebSocket Client\n(Real-Time Messaging)"]
    end

    subgraph APITier["Application Tier (FastAPI Backend)"]
        FastAPI["FastAPI 0.115+\n(Python 3.11+ / Uvicorn)"]
        Profiler["Profiler Middleware\n(SQL & Latency Telemetry)"]
        TTLCache["In-Memory TTL Cache\n(Tag-Based Invalidation)"]
        AuthModule["Dual JWT Cookie Auth\n(bcrypt / HS256)"]
        WSManager["WebSocket Connection Manager\n(Room Broadcasting)"]
    end

    subgraph ServiceTier["External AI & Cloud Integrations"]
        GroqAI["Groq AI Cloud\n(LLaMA 3.3 70B Engine)"]
        AppsScript["Google Apps Script Web App\n(Drive Storage API)"]
        GoogleDrive["Google Drive Root Folder\n(Client Subfolders)"]
    end

    subgraph DatabaseTier["Persistence Tier"]
        DB["PostgreSQL / Neon\n(SQLAlchemy 2.0 AsyncPG Pool)"]
        LocalUploads["Local Disk Fallback\n(./uploads/ Directory)"]
    end

    Browser -->|HTTPS REST| FastAPI
    Browser -->|WSS Socket| WSManager
    FastAPI --> Profiler --> TTLCache
    FastAPI --> DB
    FastAPI -->|Fast Disk Write| LocalUploads
    FastAPI -->|Async Background Sync| AppsScript --> GoogleDrive
    FastAPI -->|JSON Chat Completions| GroqAI
```

---

## 2. Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    users ||--o{ employee_clients : "assigned to"
    clients ||--o{ employee_clients : "staffed by"
    users ||--o{ sub_admin_assignments : "delegated"
    clients ||--o{ sub_admin_assignments : "scoped"
    clients ||--o{ resumes : "owns"
    users ||--o{ resumes : "uploaded by"
    clients ||--o{ requirements : "requests"
    requirements ||--o{ resumes : "tags"
    resumes ||--o{ applications : "submitted as"
    clients ||--o{ applications : "pipeline of"
    users ||--o{ applications : "managed by"
    applications ||--o{ application_events : "contains"
    email_intake ||--o{ application_events : "extracted from"
    users ||--o{ targets : "assigned to"
    clients ||--o{ targets : "scoped for"
    users ||--o{ attendance : "clocks"
    clients ||--|| chat_rooms : "has"
    chat_rooms ||--o{ chat_messages : "contains"
    users ||--o{ chat_messages : "sends"
    users ||--o{ chat_reads : "tracks cursor"
    chat_rooms ||--o{ chat_reads : "read in"
    users ||--o{ notifications : "receives"
    users ||--o{ activity_logs : "audited in"

    users {
        uuid id PK
        varchar email UK
        varchar role
        varchar status
        boolean is_active
    }
    clients {
        uuid id PK
        varchar company_name UK
        varchar status
        boolean is_active
    }
    resumes {
        uuid id PK
        varchar candidate_name
        varchar company
        varchar role
        varchar resume_id_tag
        uuid client_id FK
        uuid uploaded_by FK
        date resume_date
    }
    applications {
        uuid id PK
        uuid resume_id FK
        uuid client_id FK
        uuid employee_id FK
        varchar status
        varchar current_round
        timestamp applied_date
    }
    targets {
        uuid id PK
        uuid employee_id FK
        uuid client_id FK
        int daily_target
        varchar status
        date effective_date
    }
    attendance {
        uuid id PK
        uuid employee_id FK
        date work_date
        timestamp check_in
        timestamp check_out
        varchar total_hours
    }
```

---

## 3. Batch Resume Ingestion Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor Recruiter as Recruiter (Employee)
    participant UI as Upload Studio (/upload)
    participant Parser as Client-Side Tokenizer
    participant API as FastAPI Backend
    participant Storage as Local Storage / Drive
    participant DB as PostgreSQL Database

    Recruiter->>UI: Drag & Drop 1-100+ PDF Resumes
    UI->>Parser: Parse Filename (ServiceClient_Company_Role_ID.pdf)
    Parser-->>UI: Verified / Mismatch Status
    UI->>API: POST /api/resumes/check-duplicates
    API->>DB: Query Client Candidate Bank
    DB-->>API: Existing matches
    API-->>UI: Return Duplicate Status (Amber badges)
    Recruiter->>UI: Click "Commit Verified Resumes"
    UI->>API: POST /api/resumes/upload (Multipart)
    API->>Storage: Synchronous Disk Write (./uploads/) (< 5ms)
    API->>DB: Commit Resume & Application records
    API-->>Storage: Background Task: Sync to Google Drive
    API-->>UI: Return BulkUploadResponse
    UI->>Recruiter: Confetti Burst & Update Quota Donut
```

---

## 4. Groq AI Email Interview Intake & 4-Tier Matching

```mermaid
flowchart TD
    Start["Recruiter Pastes Interview Email\n(or uploads .eml / PDF / Screenshot)"] --> Analyze["POST /api/ai/analyze-email\n(Preview Only - 0 DB Writes)"]
    Analyze --> GroqCall["Groq LLaMA 3.3 70B API\n(temperature = 0.0)"]
    GroqCall --> Classify{"is_interview_mail ?"}

    Classify -- No --> Reject["Decision: not_related\nShow Warning Banner\nStop Execution"]
    Classify -- Yes --> Extract["Extract:\n- Candidate Name\n- Hiring Company\n- Role\n- Status & Round\n- Interview Date\n- Resume Tag"]

    Extract --> MatchScope["Search Candidate Bank\n(Scoped strictly to selected client_id)"]
    MatchScope --> Tier1{"Priority 1:\nExact Resume ID Tag Match\n(e.g. RES101) ?"}

    Tier1 -- Yes --> Link1["Link Resume (Priority 1)"]
    Tier1 -- No --> Tier2{"Priority 2:\nExact Candidate Name +\nHiring Company Match ?"}

    Tier2 -- Yes --> Link2["Link Resume (Priority 2)"]
    Tier2 -- No --> Tier3{"Priority 3:\nExact Candidate Name +\nRole Designation Match ?"}

    Tier3 -- Yes --> Link3["Link Resume (Priority 3)"]
    Tier3 -- No --> Tier4["Priority 4 Fallback:\nCreate Application with resume_id = null"]

    Link1 --> ReviewCard["Render AI Confirmation Card\n(Human Review & 1-Click Override)"]
    Link2 --> ReviewCard
    Link3 --> ReviewCard
    Tier4 --> ReviewCard

    ReviewCard --> Confirm["Recruiter clicks 'Confirm & Save'"]
    Confirm --> SaveDB["POST /api/ai/confirm-save\n1. Update Application\n2. Log Email Intake\n3. Append Application Event\n4. Post Update to Client Chat Room\n5. Dispatch In-App Notifications"]
```

---

## 5. Real-Time Chat WebSocket Flow

```mermaid
sequenceDiagram
    autonumber
    actor Recruiter as Recruiter
    participant Socket as WebSocket Channel (/api/chat/ws/{room_id})
    participant WSManager as Backend Connection Manager
    actor Client as Service Client User

    Recruiter->>Socket: Connect to Room
    Client->>Socket: Connect to Room
    Recruiter->>Socket: Typing Event { is_typing: true }
    Socket->>WSManager: Broadcast
    WSManager-->>Client: Render "Recruiter is typing..."
    Recruiter->>Socket: POST /rooms/{id}/messages (or share resume)
    WSManager->>Client: Deliver New Message & Resume Card
    Client->>Socket: Mark Read { message_id: "..." }
    WSManager-->>Recruiter: Update Read Receipt (✓✓ Read)
```

---

## 6. Daily Target Quota Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Active: Super Admin / Sub-Admin Sets Target
    Active --> Progress: Recruiter Submits Applications
    Progress --> Progress: Submission Count Increases
    Progress --> TargetMet: Submissions >= Daily Target (100% Emerald Ring)
    TargetMet --> OverAchieved: Submissions > Daily Target (> 100% + Over-achieved Badge)
    Active --> Paused: Admin Pauses Target
    Paused --> Active: Admin Resumes Target
    Active --> Ended: Target Concluded for Historical Auditing
    Ended --> [*]
```
