# LeadFlow API

A production-quality REST API for managing sales leads with FastAPI, SQLAlchemy, and SQLite.

## Project Overview

This API supports the core lead-management workflow:

- Create a lead with validation and duplicate email protection.
- List leads with optional status filtering.
- Fetch a single lead by ID.
- Update only the lead status using a dedicated endpoint.
- Register users and log in with JWT bearer tokens.
- Protect all lead routes behind authentication.

The implementation uses sync SQLAlchemy with SQLite so it is simple to run locally while still reflecting common backend engineering practices such as layered structure, typed schemas, enum validation, and explicit error handling.

## Folder Structure

```text
leadflow-api/
├── auth.py
├── database.py
├── main.py
├── models.py
├── requirements.txt
├── schemas.py
├── README.md
└── routers/
    ├── __init__.py
  ├── auth.py
    └── leads.py
```

## Setup Instructions

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the API

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

### Docker

Build and run with Compose:

```bash
docker compose up --build
```

The SQLite database is persisted in a named volume mounted at `/data/leadflow.db`.

## Health Check

`GET /health`

Example curl:

```bash
curl "http://127.0.0.1:8000/health"
```

Sample response `200 OK`:

```json
{
  "status": "ok",
  "database": {
    "connected": true
  }
}
```

## Authentication

1. Register a user with `POST /auth/register`.
2. Log in with `POST /auth/login` to receive a JWT access token.
3. Send the token on all lead requests using `Authorization: Bearer <token>`.

## API Endpoints

### 1. Register a user

`POST /auth/register`

Request body:

```json
{
  "email": "admin@leadflow.com",
  "password": "StrongPass123!",
  "full_name": "LeadFlow Admin"
}
```

Example curl:

```bash
curl -X POST "http://127.0.0.1:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"admin@leadflow.com\",\"password\":\"StrongPass123!\",\"full_name\":\"LeadFlow Admin\"}"
```

Sample response `201 Created`:

```json
{
  "id": 1,
  "email": "admin@leadflow.com",
  "full_name": "LeadFlow Admin",
  "is_active": true
}
```

### 2. Log in

`POST /auth/login`

Request body:

```json
{
  "email": "admin@leadflow.com",
  "password": "StrongPass123!"
}
```

Example curl:

```bash
curl -X POST "http://127.0.0.1:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"admin@leadflow.com\",\"password\":\"StrongPass123!\"}"
```

Sample response `200 OK`:

```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer"
}
```

### 3. Create a lead

`POST /leads`

Request body:

```json
{
  "name": "Ava Johnson",
  "email": "ava@acme.com",
  "company": "Acme Inc",
  "phone": "+1-555-0100",
  "source": "website",
  "status": "new"
}
```

Example curl:

```bash
curl -X POST "http://127.0.0.1:8000/leads" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d "{\"name\":\"Ava Johnson\",\"email\":\"ava@acme.com\",\"company\":\"Acme Inc\",\"phone\":\"+1-555-0100\",\"source\":\"website\",\"status\":\"new\"}"
```

Sample response `201 Created`:

```json
{
  "name": "Ava Johnson",
  "email": "ava@acme.com",
  "company": "Acme Inc",
  "phone": "+1-555-0100",
  "source": "website",
  "status": "new",
  "id": 1
}
```

Duplicate email response `409 Conflict`:

```json
{
  "detail": "A lead with this email already exists."
}
```

### 4. Fetch all leads

`GET /leads`

Optional filter:

- `status=new`
- `status=contacted`
- `status=qualified`
- `status=lost`
- `status=converted`

Example curl:

```bash
curl "http://127.0.0.1:8000/leads?status=new" \
  -H "Authorization: Bearer <token>"
```

Sample response `200 OK`:

```json
[
  {
    "name": "Ava Johnson",
    "email": "ava@acme.com",
    "company": "Acme Inc",
    "phone": "+1-555-0100",
    "source": "website",
    "status": "new",
    "id": 1
  }
]
```

### 5. Fetch a single lead

`GET /leads/{id}`

Example curl:

```bash
curl "http://127.0.0.1:8000/leads/1" \
  -H "Authorization: Bearer <token>"
```

Sample response `200 OK`:

```json
{
  "name": "Ava Johnson",
  "email": "ava@acme.com",
  "company": "Acme Inc",
  "phone": "+1-555-0100",
  "source": "website",
  "status": "new",
  "id": 1
}
```

If the ID does not exist, the API returns `404 Not Found`:

```json
{
  "detail": "Lead not found."
}
```

### 6. Update lead status

`PATCH /leads/{id}/status`

Allowed values:

- `new`
- `contacted`
- `qualified`
- `lost`
- `converted`

Example curl:

```bash
curl -X PATCH "http://127.0.0.1:8000/leads/1/status" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d "{\"status\":\"qualified\"}"
```

Sample response `200 OK`:

```json
{
  "name": "Ava Johnson",
  "email": "ava@acme.com",
  "company": "Acme Inc",
  "phone": "+1-555-0100",
  "source": "website",
  "status": "qualified",
  "id": 1
}
```

If the status value is invalid, FastAPI returns `422 Unprocessable Entity`.

### 7. View lead activity history

`GET /leads/{id}/activity`

Example curl:

```bash
curl "http://127.0.0.1:8000/leads/1/activity" \
  -H "Authorization: Bearer <token>"
```

Sample response `200 OK`:

```json
[
  {
    "id": 1,
    "lead_id": 1,
    "previous_status": "new",
    "new_status": "contacted",
    "changed_at": "2026-05-19T12:30:00Z"
  },
  {
    "id": 2,
    "lead_id": 1,
    "previous_status": "contacted",
    "new_status": "qualified",
    "changed_at": "2026-05-19T12:45:00Z"
  }
]
```

## Design Decisions

### Why FastAPI

FastAPI gives strong request validation, automatic OpenAPI docs, type-driven development, and a clean dependency injection model. That makes it a strong fit for a polished internship-ready backend.

### Why SQLAlchemy ORM

SQLAlchemy provides a realistic ORM layer used in production systems, keeps the data access code readable, and makes it easy to evolve the schema later without rewriting route handlers.

### Why SQLite

SQLite keeps the project zero-dependency for local setup and review while still using the same ORM patterns you would use against PostgreSQL or MySQL in a real deployment.

### Why sync architecture

A sync stack is simpler for a compact CRUD API, easy to reason about, and matches the requested tech stack. It also keeps the code approachable for reviewers.

### Why enums and explicit error handling

The status enum prevents invalid workflow states, while explicit 404, 409, and 500 handling makes the API behavior predictable and easier to integrate with.
