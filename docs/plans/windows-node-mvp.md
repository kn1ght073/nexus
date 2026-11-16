# NEXUS — Phase 1 Implementation Plan: Core Node MVP

Now that our repository and branches are perfectly set up, it's time to build the foundation of the NEXUS ecosystem: the **Central API Node**.

We are currently on the `feature/windows-node-mvp` branch.

## User Review Required

> [!IMPORTANT]  
> Please review the architecture choices for the backend API. I have mapped out a robust Python/FastAPI structure that will easily integrate with the future local AI layer. Let me know if you approve this structure so I can begin writing the code!

## Open Questions

- Do you have `uv` (the fast Python package manager) installed, or should I proceed using the standard `pip`/`venv` workflow for setting up the Python environment? (I recommend `pip` standard `venv` to keep it universally accessible unless you prefer otherwise).
- For the MVP, we will mock the authentication to keep progress fast, but eventually, we'll need real token-based auth. Is mocking okay for now?

## Proposed Changes

We will build the **NEXUS Core API** inside `services/core-api/`. 

### Technology Stack
- **Framework:** FastAPI (Python)
- **Server:** Uvicorn
- **Database:** SQLite (local file)
- **ORM:** SQLAlchemy
- **Data Validation:** Pydantic

### Component Structure
We will create the following files in `services/core-api/`:

#### [NEW] `requirements.txt`
Dependencies: `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`.

#### [NEW] `main.py`
The FastAPI application entry point, including a `/health` route.

#### [NEW] `database.py`
SQLAlchemy engine and session setup for a local SQLite database (`nexus.db`).

#### [NEW] `models.py`
Database models (SQLAlchemy) for the MVP entities:
- `User`
- `Device`
- `Project`
- `Task`
- `Note`

#### [NEW] `schemas.py`
Pydantic schemas for data validation (Request/Response models corresponding to the DB entities).

#### [NEW] `api.py` (or individual route files)
API Endpoints:
- `POST /auth/login` (Mock)
- `POST /devices/register`
- `GET /projects`, `POST /projects`
- `GET /tasks`, `POST /tasks`
- `GET /notes`, `POST /notes`

## Verification Plan

### Automated Tests
- Once the basic structure is running, we will add simple `pytest` integration to verify the endpoints.

### Manual Verification
1. Activate the Python virtual environment and run the server using `uvicorn main:app --reload`.
2. Navigate to `http://localhost:8000/docs` to view the auto-generated Swagger UI.
3. Manually test the `/health` endpoint and use the Swagger UI to create a project and a task, verifying that they persist in the SQLite database.
4. Commit the changes to `feature/windows-node-mvp`.
