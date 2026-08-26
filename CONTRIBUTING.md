# Contributing to ApplyFlow

Thank you for your interest in contributing to **ApplyFlow**! We welcome bug reports, feature proposals, and code contributions.

---

## 🛠️ Development Setup

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** and **npm**
- **PostgreSQL 15+** (optional; SQLite supported for local development)

### 1. Fork & Clone Repository
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
cp .env.example .env
python seed.py
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Testing & Code Quality

Before submitting a Pull Request, ensure that all tests and lint checks pass:

### Run Backend Unit & Integration Tests
```bash
cd backend
pytest tests/ -v
python test_master_qa_suite.py
```

### Run Frontend Build Check
```bash
cd frontend
npm run build
```

---

## 🌿 Branching & Commit Guidelines

- **Branch Naming**:
  - `feature/feature-name`
  - `fix/bug-description`
  - `docs/documentation-update`
- **Commit Messages**: Follow [Conventional Commits](https://www.conventionalcommits.org/):
  - `feat: add Google Drive automatic retry handler`
  - `fix: correct target quota completion calculation`
  - `docs: update deployment guidelines in README`

---

## 📬 Pull Request Checklist
- [ ] Code follows standard formatting conventions (PEP 8 for Python, Prettier/ESLint for JavaScript/React).
- [ ] Unit tests are written and pass with 100% success rate.
- [ ] No personal tokens, API keys, or sensitive credentials are committed.
- [ ] Updated relevant documentation or README if adding new features.

---

## 📄 License
By contributing to ApplyFlow, you agree that your contributions will be licensed under the [MIT License](LICENSE).
