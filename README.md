# Project Matilda — AI Historical Representation Auditor

Project Matilda is an AI-powered historical representation auditing system for educational materials. It identifies historically significant women whose contributions are omitted, underrepresented, credit-displaced, or minimized in text.

---

## Repository Structure

```text
.
├── backend/          # FastAPI application, core configuration, and health endpoints
├── frontend/         # Next.js (TypeScript + Tailwind CSS) client application
├── infrastructure/   # Container orchestration and deployment configurations
├── docs/             # Architecture specifications and documentation
└── scripts/          # Developer tooling and bootstrapping scripts
```

---

## Local Development Quickstart

### Prerequisites
* Python 3.11+
* Node.js 18+
* Docker (optional)

### 1. Environment Setup
```bash
cp .env.example .env
```

### 2. Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```
API Documentation: `http://localhost:8000/docs`  
Health Endpoint: `http://localhost:8000/api/v1/health`

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend App: `http://localhost:3000`

### 4. Running Quality & Test Checks
```bash
# Backend Quality
cd backend
ruff check .
mypy app
pytest

# Frontend Quality
cd frontend
npm run lint
npx tsc --noEmit
```
