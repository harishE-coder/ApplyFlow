# ApplyFlow ATS — Deployment & Environment Configuration Guide

This guide details how to configure, run, and deploy ApplyFlow across all three supported database environments:
1. **Local SQLite** (Fastest 0-setup local mode)
2. **Local PostgreSQL** (Docker containerized)
3. **Production: Render + Vercel + Neon PostgreSQL (Singapore Region)**

---

## 1. Environment Priority Architecture

ApplyFlow automatically resolves the database connection in `backend/app/core/config.py` using this strict priority order:

```mermaid
flowchart TD
    A[Start Backend Engine] --> B{Is DATABASE_URL set in env?}
    B -- Yes (Production) --> C[Use DATABASE_URL (Neon Singapore / Render)]
    B -- No --> D{Is USE_SQLITE=true?}
    D -- Yes (Local SQLite) --> E[Use sqlite+aiosqlite:///./applyflow.db]
    D -- No (Local Postgres) --> F[Use postgresql+asyncpg://localhost:5432/applyflow]
```

---

## 2. Environment 1 — Local Quickstart with SQLite

Zero dependencies, sub-millisecond local queries. Ideal for UI testing, offline work, and quick development.

### Backend Setup
In `backend/.env`:
```env
USE_SQLITE=true
DATABASE_URL=

JWT_SECRET_KEY=dev-secret-key-applyflow-2026
ADMIN_EMAIL=Harishabblu123@gmail.com
ADMIN_PASSWORD=Harish@2007
FRONTEND_URL=http://localhost:5173
```

Run migrations & start backend:
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python seed.py
uvicorn app.main:app --reload --port 8000
```

---

## 3. Environment 2 — Local PostgreSQL (Docker)

Recommended for full local development matching PostgreSQL production behavior.

### 1. Launch PostgreSQL Container
```bash
docker run --name applyflow-db \
  -e POSTGRES_USER=applyflow_user \
  -e POSTGRES_PASSWORD=strong_password \
  -e POSTGRES_DB=applyflow \
  -p 5432:5432 \
  -d postgres:16-alpine
```

*Or use docker-compose from the project root:*
```bash
docker compose up -d
```

### 2. Configure Backend `.env`
In `backend/.env`:
```env
USE_SQLITE=false
DATABASE_URL=

DB_HOST=localhost
DB_PORT=5432
DB_NAME=applyflow
DB_USER=applyflow_user
DB_PASSWORD=strong_password

JWT_SECRET_KEY=dev-secret-key-applyflow-2026
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

ADMIN_EMAIL=Harishabblu123@gmail.com
ADMIN_PASSWORD=Harish@2007
FRONTEND_URL=http://localhost:5173
```

### 3. Run Migrations & Start Server
```bash
cd backend
source venv/bin/activate
alembic upgrade head
python seed.py
uvicorn app.main:app --reload --port 8000
```

---

## 4. Environment 3 — Production (Render + Neon Singapore + Vercel)

Production deployment with serverless Neon PostgreSQL hosted in **Singapore (`ap-southeast-1`)** for sub-30ms Asian regional latency.

### 1. Neon PostgreSQL Database (Singapore)
1. Go to [Neon Console](https://console.neon.tech).
2. Create a Project in Region: **Asia Pacific (Singapore) `ap-southeast-1`**.
3. Copy the pooled connection string (`-pooler` endpoint recommended for serverless connection pooling). Example:
   ```
   postgresql://neondb_owner:YOUR_PASSWORD@ep-sample-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
   ```

### 2. Render Backend Web Service
1. Create a new **Web Service** on [Render](https://render.com).
2. Connect your Git repository.
3. Configure Build & Start Commands:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r backend/requirements.txt && alembic upgrade head`
   - **Start Command:** `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Set Environment Variables in Render:

| Variable | Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://neondb_owner:...@ep-...-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require` | Neon Singapore connection string |
| `JWT_SECRET_KEY` | *(Generate a 64-char random hex key)* | Production JWT encryption key |
| `JWT_ALGORITHM` | `HS256` | Token signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Access token lifespan |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifespan |
| `ADMIN_NAME` | `Harish Admin` | Initial Admin Account |
| `ADMIN_EMAIL` | `Harishabblu123@gmail.com` | Initial Admin Login Email |
| `ADMIN_PASSWORD` | *(Your Secure Admin Password)* | Initial Admin Password |
| `FRONTEND_URL` | `https://your-applyflow.vercel.app` | Production Frontend domain for CORS |
| `GROQ_API_KEY` | *(Optional Groq API key)* | Email AI parsing engine |
| `GOOGLE_APPS_SCRIPT_URL` | *(Optional Apps Script URL)* | Google Drive cloud sync |
| `GOOGLE_DRIVE_ROOT_FOLDER_ID` | *(Optional Drive Folder ID)* | Personal Google Drive folder |

### 3. Vercel Frontend Deployment
1. Import repository to [Vercel](https://vercel.com).
2. **Root Directory:** `frontend`
3. **Framework Preset:** `Vite`
4. **Build Command:** `npm run build`
5. **Output Directory:** `dist`
6. In `frontend/vite.config.js` or Vercel `vercel.json`, configure API reverse proxy to forward `/api` requests to your Render backend URL:
   ```json
   {
     "rewrites": [
       { "source": "/api/(.*)", "destination": "https://your-render-app.onrender.com/api/$1" },
       { "source": "/(.*)", "destination": "/index.html" }
     ]
   }
   ```

---

## 5. Verification & Health Checks

Verify your deployment with these commands:

### Check Backend Health
```bash
curl -i http://localhost:8000/api/health
```
*Expected Response:*
```json
HTTP/1.1 200 OK
{"status":"healthy","service":"ApplyFlow Careers API"}
```

### Run Backend Automated Test Suites
```bash
cd backend
pytest
python test_master_qa_suite.py
python test_global_date_filters_and_pipeline.py
python test_client_dashboard.py
```

### Validate Frontend Production Build
```bash
cd frontend
npm run build
```

---

## 6. Performance Benchmarks

| Action | Target | Achieved Mechanism |
| :--- | :--- | :--- |
| **Login** | < 300ms | In-memory token decode + connection pool keep-alive |
| **Dashboard** | < 700ms | Tag-based in-memory TTL caching (20s) |
| **Candidate Bank** | < 250ms | Indexed single-pass queries + pagination |
| **Resume Upload Response** | < 150ms | Sub-ms local write + asynchronous `BackgroundTasks` Google Drive sync |
| **Notification Polling** | < 50ms | In-memory TTL cache (10s) with tagged invalidations |
| **N+1 SQL Reduction** | Down to 1–3 queries | Consolidated `GROUP BY` aggregate dictionaries |
