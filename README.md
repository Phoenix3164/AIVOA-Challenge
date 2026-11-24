# PharmaRCA AI – Intelligent Pharmaceutical Root Cause Analysis

An AI-powered Root Cause Analysis (RCA) platform designed for pharmaceutical API manufacturing. PharmaRCA helps quality teams investigate manufacturing deviations by extracting information from documents, identifying potential root causes, highlighting missing evidence, and generating reviewable Corrective and Preventive Action (CAPA) recommendations.

The platform combines **React, FastAPI, LangGraph and Groq** to support an AI-assisted investigation workflow while keeping the investigator in control of final decisions.

---

## Overview

Pharmaceutical manufacturing deviations require structured investigation, evidence collection, root cause identification and appropriate corrective and preventive actions.

PharmaRCA provides a centralized workspace where investigators can upload deviation documents, extract relevant information, review AI-generated suggestions, manage investigations and generate investigation reports.

The application follows a human-in-the-loop approach: AI-generated findings and CAPA recommendations remain subject to investigator and QA review.

---

## Key Features

### 1. AI-Powered PDF Extraction
- Upload deviation and investigation PDF documents.
- Extract relevant text using PyMuPDF.
- Identify important investigation information.
- Automatically populate corresponding investigation form fields.
- Keep unavailable information blank instead of inventing values.
- Review and edit extracted information before saving.

### 2. AI Root Cause Analysis
- Analyze deviation information using the AI workflow.
- Generate potential root cause hypotheses.
- Perform Five Whys analysis.
- Generate Fishbone analysis.
- Identify contributing factors and areas requiring investigation.
- Distinguish potential causes from confirmed findings.

### 3. Evidence Gap Identification
- Identify missing investigation information.
- Highlight records and evidence required for further investigation.
- Help investigators identify what additional information should be collected.

### 4. CAPA Management
- Generate provisional CAPA recommendations.
- Organize recommendations into:
  - Correction
  - Corrective Action
  - Preventive Action
- Link CAPA recommendations to their corresponding RCA investigations.
- Track review status.
- Support investigator review and editing.

### 5. Investigation Management
- Create and save RCA investigations.
- Maintain investigation records in the database.
- Associate uploaded documents and analysis results with investigations.
- View and reopen saved investigations.
- Preserve investigation information for continued review.

### 6. Reports
- Provide an investigation reporting workspace.
- Organize investigation information and analysis results.
- Support structured RCA reporting and PDF export where enabled.

### 7. AI Copilot
- Interact with the investigation through a chatbot.
- Ask questions about uploaded documents.
- Request investigation assistance.
- Support conversational interactions and follow-up questions.

---

## Technology Stack

| Component | Technologies |
|---|---|
| Frontend | React 19, Vite, TypeScript |
| State Management | Redux Toolkit |
| UI / Forms | React Hook Form, Tailwind CSS |
| Routing | React Router |
| API Communication | Axios |
| Backend | Python, FastAPI |
| AI Workflow | LangGraph, LangChain |
| LLM | Groq API |
| PDF Processing | PyMuPDF |
| Database ORM | SQLAlchemy |
| Database | SQLite / MySQL |
| Migrations | Alembic |
| Testing | Pytest |

---

## Application Architecture

```text
                 USER
                  |
                  v
       REACT + VITE FRONTEND
                  |
          Redux Toolkit
                  |
             Axios API
                  |
                  v
          FASTAPI BACKEND
                  |
          LANGGRAPH WORKFLOW
                  |
        +---------+----------+
        |         |          |
        v         v          v
     PDF       GROQ LLM    RULE-BASED
  EXTRACTION   ANALYSIS     FALLBACK
        |         |          |
        +---------+----------+
                  |
                  v
          RCA ANALYSIS
                  |
        +---------+----------+
        |         |          |
        v         v          v
     FIVE      EVIDENCE     CAPA
     WHYS        GAPS    RECOMMENDATIONS
        |         |          |
        +---------+----------+
                  |
                  v
          SQLALCHEMY ORM
                  |
                  v
           DATABASE
          SQLite / MySQL
                  |
                  v
       SAVED INVESTIGATIONS
                  |
                  v
          REPORTING WORKSPACE
```

---

## Application Workflow

1. The investigator creates a new RCA investigation.
2. A deviation PDF is uploaded through the AI Copilot.
3. The backend extracts the document text.
4. The AI workflow identifies relevant incident information.
5. Extracted information populates the investigation form.
6. The investigator reviews and edits the extracted information.
7. The RCA workflow generates potential root causes, Five Whys and Fishbone analysis.
8. The system identifies missing evidence.
9. Provisional CAPA recommendations are generated.
10. Investigation information and associated analysis are saved in the database.
11. The investigator can reopen the investigation and continue reviewing it.
12. Investigation information can be used in the reporting workflow.

---

## Project Structure

```text
AIVOA-Challenge/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── ai_graph.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── ...
│   │
│   ├── tests/
│   ├── requirements.txt
│   ├── .env.example
│   └── ...
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── store.ts
│   │   ├── types.ts
│   │   └── ...
│   │
│   ├── package.json
│   └── ...
│
├── PharmaRCA_Test_Deviation_Report.pdf
├── .gitignore
├── README.md
└── package-lock.json
```

---

## Getting Started

### Prerequisites

Install the following before running the application:

- Python 3.10 or later
- Node.js and npm
- Git
- Groq API key (optional for demo mode)

### 1. Clone the Repository

```bash
git clone https://github.com/Phoenix3164/AIVOA-Challenge.git

cd AIVOA-Challenge
```

### 2. Backend Setup

Navigate to the backend folder:

```powershell
cd backend
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file inside the `backend` directory by copying `.env.example`.

```powershell
Copy-Item .env.example .env
```

Configure the environment variables:

```env
DATABASE_URL=sqlite:///./pharmarca.db

SECRET_KEY=replace-with-a-secure-secret

GROQ_API_KEY=your_groq_api_key

GROQ_MODEL=qwen/qwen3.8-27b

DEMO_MODE=false
```

**Note:**
- Keep your actual API key private.
- Never commit your `.env` file.
- Groq integration requires a valid API key and supported model.
- The application also provides a demo/fallback configuration.

### 4. Start the Backend

From the `backend` directory:

```powershell
uvicorn app.main:app --reload --port 8000
```

Backend API:

```text
http://localhost:8000
```

Interactive API documentation:

```text
http://localhost:8000/docs
```

### 5. Frontend Setup

Open a second terminal:

```powershell
cd frontend
```

Install dependencies:

```powershell
npm install
```

Start the development server:

```powershell
npm run dev
```

Open the Vite URL displayed in your terminal, normally:

```text
http://localhost:5173
```

---

## Demo Login

The repository provides a preloaded QA demo account:

| Field | Value |
|---|---|
| Email | qa@pharmarca.local |
| Password | demo123 |

Use these credentials only for the local demonstration environment.

---

## Database Configuration

The project supports SQLite for local demonstration and MySQL configuration.

**SQLite (default):**

```env
DATABASE_URL=sqlite:///./pharmarca.db
```

**MySQL example:**

```env
DATABASE_URL=mysql+pymysql://username:password@localhost/pharmarca
```

For the MySQL configuration, apply the available database migrations:

```bash
alembic upgrade head
```

---

## Testing

### Backend Tests

From the backend directory:

```bash
pytest
```

### Frontend Production Build

From the frontend directory:

```bash
npm run build
```

### Frontend Lint

```bash
npm run lint
```

---

## Sample PDF for Testing

The repository includes:

`PharmaRCA_Test_Deviation_Report.pdf`

This is a synthetic pharmaceutical deviation report created for testing the application's PDF extraction and RCA workflow.

It contains demonstration information about:

- Metformin Hydrochloride API
- Batch MET26118
- Moisture content deviation
- Manufacturing process parameters
- Evidence gaps
- Potential investigation avenues
- Provisional CAPA recommendations

**Important:** The sample document is fictional and is not a genuine GMP manufacturing or laboratory record. Its root cause is intentionally not established.

---

## Human-in-the-Loop Approach

PharmaRCA is designed as an AI-assisted decision-support application, not an autonomous pharmaceutical quality approval system.

- Extracted information requires investigator verification.
- Potential root causes require supporting evidence.
- Missing evidence must be identified rather than fabricated.
- CAPA recommendations remain provisional until reviewed.
- Batch disposition and quality decisions remain with authorized personnel.

AI-generated suggestions must not replace approved pharmaceutical quality procedures or qualified QA decisions.

---

## Future Enhancements

Potential areas for further development include:

- Advanced investigation analytics and dashboards.
- More comprehensive audit trails.
- Role-based access control.
- Investigation approval workflows.
- Enhanced CAPA effectiveness tracking.
- Additional document formats and extraction capabilities.
- Production database deployment.
- Automated report distribution.

---

## Author

**Yash Kunjir**

GitHub: [@Phoenix3164](https://github.com/Phoenix3164)

Project Repository: [PharmaRCA – AIVOA Challenge](https://github.com/Phoenix3164/AIVOA-Challenge)

---

## Disclaimer

This project is an AI-assisted pharmaceutical RCA demonstration developed as part of an engineering challenge.

It is intended for educational and demonstration purposes. It is not a validated pharmaceutical quality management system and must not be used as a substitute for regulated GMP processes, approved investigation procedures, or qualified quality decisions.
