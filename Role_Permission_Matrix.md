# ApplyFlow ATS — Complete Role & Permission Matrix (RBAC)

> **Specification Version**: 1.2.0  
> **Enforcement Standard**: Dual-Layer Authorization (FastAPI `dependencies.py` Authoritative Backend Layer + React Router `ProtectedRoute` Frontend View Guard)

---

## 1. System Roles Definition

1. **Super Admin (`admin`)**: Complete platform and company authority.
2. **Sub-Admin (`sub_admin`)**: Delegated operational management over assigned clients and recruiters.
3. **Employee / Recruiter (`employee`)**: Candidate sourcing, bulk ingestion, interview advancement, and client delivery.
4. **Service Client (`client`)**: Customer portal access to review talent, track interview pipeline, and chat with recruiters.

---

## 2. Master Permission Matrix

| Module / Operation | Super Admin | Sub-Admin | Employee (Recruiter) | Service Client |
| :--- | :---: | :---: | :---: | :---: |
| **Authentication & Profile** | | | | |
| Sign in with Email / Password | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| Silent Token Refresh | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| View Own Profile (`/me`) | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| Universal Bootstrap (`/bootstrap`) | ✅ Global | ✅ Scoped | ✅ Assigned | ✅ Client Only |
| **Dashboard & Telemetry** | | | | |
| View Global Agency Analytics | ✅ Full | ❌ Forbidden | ❌ Forbidden | ❌ Forbidden |
| View Scoped Client Analytics | ✅ Full | ✅ Assigned | ❌ Forbidden | ❌ Forbidden |
| View Personal Quota & Donut Ring | ❌ N/A | ❌ N/A | ✅ Exclusive | ❌ Forbidden |
| View Customer Candidate Portal | ❌ N/A | ❌ N/A | ❌ N/A | ✅ Exclusive |
| View System SQL Telemetry (`/performance`)| ✅ Full | ✅ Scoped | ❌ Forbidden | ❌ Forbidden |
| **Resume & Ingestion Engine** | | | | |
| Bulk PDF Upload (`/upload`) | ❌ **Protected** | ❌ **Protected** | ✅ **Exclusive** | ❌ **Protected** |
| Manual Metadata Review Confirmation | ❌ Forbidden | ❌ Forbidden | ✅ Exclusive | ❌ Forbidden |
| View All Agency Resumes | ✅ Full | ❌ Forbidden | ❌ Forbidden | ❌ Forbidden |
| View Scoped Client Resumes | ✅ Full | ✅ Assigned | ✅ Assigned | ✅ Client Only |
| Stream PDF Inline (`/preview`) | ✅ Full | ✅ Scoped | ✅ Scoped | ✅ Scoped |
| Download Raw PDF (`/download`) | ✅ Full | ✅ Scoped | ✅ Scoped | ✅ Scoped |
| Edit Candidate Notes (Private) | ✅ Full | ✅ Scoped | ✅ Scoped | ❌ Read Shared |
| Edit Candidate Notes (Shared) | ✅ Full | ✅ Scoped | ✅ Scoped | ❌ Read Only |
| Delete Candidate Resume | ✅ Full | ✅ Scoped | ✅ Own Uploads | ❌ Forbidden |
| **AI Interview Email Intake** | | | | |
| Paste / Upload Email for Analysis | ✅ Global | ✅ Scoped | ✅ Assigned | ❌ Forbidden |
| Preview Groq LLaMA 3.3 Extraction | ✅ Global | ✅ Scoped | ✅ Assigned | ❌ Forbidden |
| Confirm & Persist AI Event | ✅ Global | ✅ Scoped | ✅ Assigned | ❌ Forbidden |
| View AI Response Inbox Feed | ✅ Global | ✅ Scoped | ✅ Assigned | ❌ Forbidden |
| **Application Pipeline** | | | | |
| Create Application from Candidate Bank | ✅ Full | ✅ Scoped | ✅ Assigned | ❌ Read Only |
| Advance Application Stage / Round | ✅ Full | ✅ Scoped | ✅ Assigned | ❌ Read Only |
| View Candidate Event Timeline | ✅ Full | ✅ Scoped | ✅ Scoped | ✅ Scoped |
| Close Application (Process Finished) | ✅ Full | ✅ Scoped | ✅ Scoped | ❌ Forbidden |
| Archive Application | ✅ Full | ✅ Scoped | ✅ Scoped | ❌ Forbidden |
| Permanently Delete Application | ✅ **Exclusive** | ❌ Forbidden | ❌ Forbidden | ❌ Forbidden |
| **Service Client Management** | | | | |
| Create Service Client | ✅ Full | ✅ Auto-assigned | ❌ Forbidden | ❌ Forbidden |
| Update Client Details / Logo | ✅ Full | ✅ Scoped | ❌ Forbidden | ❌ Forbidden |
| Assign / Unassign Recruiters | ✅ Full | ✅ Scoped | ❌ Forbidden | ❌ Forbidden |
| Deactivate / Reactivate Client | ✅ Full | ✅ Scoped | ❌ Forbidden | ❌ Forbidden |
| Archive Service Client | ✅ Full | ✅ Scoped | ❌ Forbidden | ❌ Forbidden |
| Safe Delete Service Client | ✅ **Exclusive** | ❌ Forbidden | ❌ Forbidden | ❌ Forbidden |
| **Sub-Admin Delegation** | | | | |
| Provision Sub-Admin Account | ✅ **Exclusive** | ❌ Forbidden | ❌ Forbidden | ❌ Forbidden |
| Assign Clients / Teams to Sub-Admin | ✅ **Exclusive** | ❌ Forbidden | ❌ Forbidden | ❌ Forbidden |
| **Job Openings & Requirements** | | | | |
| Create Requisition | ✅ Full | ✅ Scoped | ✅ Assigned | ❌ Forbidden |
| Edit Requisition Details | ✅ Full | ✅ Scoped | ✅ Assigned | ❌ Forbidden |
| Mark Requisition Done / Completed | ✅ Full | ✅ Scoped | ✅ Assigned | ❌ Forbidden |
| Reopen Requisition | ✅ Full | ✅ Scoped | ✅ Assigned | ❌ Forbidden |
| Delete Requisition | ✅ Full | ✅ Scoped | ❌ Forbidden | ❌ Forbidden |
| **Daily Targets & Quotas** | | | | |
| Create / Set Daily Target | ✅ Full | ✅ Scoped Team | ❌ Forbidden | ❌ Forbidden |
| Pause / Resume Target | ✅ Full | ✅ Scoped Team | ❌ Forbidden | ❌ Forbidden |
| End Target | ✅ Full | ✅ Scoped Team | ❌ Forbidden | ❌ Forbidden |
| Delete Future Target | ✅ Full | ✅ Scoped Team | ❌ Forbidden | ❌ Forbidden |
| View Personal Target Progress | ✅ Scoped View | ✅ Scoped View | ✅ Live Donut | ❌ Forbidden |
| **Shift Attendance** | | | | |
| Shift Check-In (`/check-in`) | ❌ N/A | ❌ N/A | ✅ Exclusive | ❌ Forbidden |
| Shift Check-Out (`/check-out`) | ❌ N/A | ❌ N/A | ✅ Exclusive | ❌ Forbidden |
| View Live Attendance Summary | ✅ Full | ✅ Scoped | ❌ Personal Only | ❌ Forbidden |
| **Real-Time Client Chat** | | | | |
| Access Chat Room | All Rooms | Scoped Rooms | Assigned Rooms | Own Client Room |
| Send Text Message | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| Share Candidate Resume into Chat | ✅ Full | ✅ Full | ✅ Full | ❌ View Only |
| Lock Room (Read-Only Mode) | ✅ Full | ✅ Scoped | ❌ Forbidden | ❌ Forbidden |
| Archive Chat Room | ✅ Full | ✅ Scoped | ❌ Forbidden | ❌ Forbidden |
| Export Chat Transcript | ✅ Full | ✅ Scoped | ✅ Assigned | ✅ Own Room |
| Delete Chat Message | ✅ Sender / Admin | ✅ Sender / Admin | ✅ Own Message | ✅ Own Message |
| **Reports & Exports** | | | | |
| Download Master Excel (`.xlsx`) | ✅ Full Global | ✅ Scoped Data | ❌ Forbidden | ❌ Forbidden |
| Generate Executive PDF Summary | ✅ Full Global | ✅ Scoped Data | ❌ Assigned | ✅ Client PDF |
| Export CSV Operational Data | ✅ Full Global | ✅ Scoped Data | ❌ Forbidden | ❌ Forbidden |
| **Activity Audit Logs** | | | | |
| Query Security Audit Logs | ✅ All Logs | ❌ Personal | ❌ Personal | ❌ Personal |

---

## 3. Critical Security Boundaries

1. **Recruiter Accountability Boundary**:
   - Super Admins and Sub-Admins cannot upload resumes directly (`/upload`). This guarantees that every ingested candidate profile is attributable to a specific talent recruiter.
2. **Multi-Tenant Customer Isolation (IDOR Prevention)**:
   - Candidate queries in the service layer enforce `get_allowed_client_ids(db, current_user)`. Even if an attacker manipulates a `client_id` parameter in an API request, the query returns HTTP 403 Forbidden if the client is outside their assigned scope.
3. **Safe Deletion Cascade Integrity**:
   - Permanent deletion of clients is prohibited if historical resumes, applications, or chat messages are attached.
