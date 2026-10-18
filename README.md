# MedFlow — Hospital Data Management

A lightweight, responsive hospital-operations prototype built with Flask, SQLite, HTML, CSS, and vanilla JavaScript. It demonstrates patient registration, appointment scheduling, supply inventory, and a context-aware operations assistant.

> **Safety and privacy:** This is an educational demo, not a certified hospital information system. Seed data is fictional. Do not enter real patient/health information or deploy with real data. Production use would require a formal privacy/security review, stronger identity and role controls, encryption and key management, backups, monitoring, retention policies, and compliance with applicable law.

## Chosen vertical and persona

**Vertical:** Healthcare / hospital operations. **Primary persona:** a hospital front-desk or operations administrator who needs a single place to coordinate patient registration, appointment flow, and basic consumables inventory.

## Features

- **Operations dashboard:** counts patient records, today's non-cancelled appointments, records marked admitted, and inventory items at/below reorder level.
- **Patient directory:** search by name, medical record number (MRN), or department; register records; view basic demographic and appointment history.
- **Appointment desk:** schedule a visit for a registered patient and update status (Scheduled, Checked in, Completed, Cancelled).
- **Inventory:** create items, record quantity/reorder thresholds, and apply signed adjustments without allowing stock to become negative.
- **Context-aware operations assistant:** reads current SQLite records to answer questions about today's appointments, low stock, and admission counts; routes record-finding questions to the directory. It does not diagnose, triage symptoms, or recommend treatment.
- **Security foundations:** password hashing, login-protected pages, session cookie flags, CSRF token checks for mutations, server-side validation, parameterized SQL, HTML auto-escaping, safe `textContent` rendering, and a basic audit log.
- **Responsive accessible UI:** semantic labels, keyboard-friendly forms, live status area for assistant replies, reduced-motion support, and responsive layout.

## How the logic works

1. Flask checks the session before rendering operational routes.
2. SQLite stores users, patient records, appointments, inventory, and a basic audit trail.
3. Dashboard metrics are computed from live database queries, not hard-coded counters.
4. The assistant classifies the user's operational question using small, transparent keyword rules and queries the relevant tables. Responses are grounded in the demo database. Unknown requests receive a capability explanation.
5. Inventory items are flagged when `quantity <= reorder_level`; adjustments that would make stock negative are rejected.

## Run locally

Requires Python 3.10+.

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>.

Demo login: `admin` / `ChangeMe123!`. Change this immediately before any sharing. You can set `DEMO_PASSWORD` before first database initialization to seed a different password. The app creates `medflow.db` in the project directory on first run; this file is ignored by Git.

For a stable secret, set `SECRET_KEY` in your environment. When running behind HTTPS, set `COOKIE_SECURE=1`. Do not enable Flask debug mode in a shared or production environment.

## Evaluation map (challenge rubric)

| Criterion | Evidence in this repository | Validation approach |
|---|---|---|
| Code quality | Flask routes grouped by workflow, reusable authentication/CSRF/audit helpers, parameterized SQL, Jinja templates and static assets separated from Python | Python compilation and focused route tests |
| Security | Werkzeug password hashing, login-required decorator, CSRF checks on mutations, same-origin redirect validation, HTTP-only/SameSite cookies, secure cookies on Vercel, response security headers, payload limits and input validation | Tests for CSRF, authentication, open redirects, error responses and invalid inputs |
| Efficiency | Database indexes for patient lookup/status, appointment date/status, patient appointment history, stock alerts and audit time; patient results paginated at 50 per page; dashboard result sets are capped | Schema index test and bounded result-set review |
| Testing | Automated Flask test client suite for positive and negative paths, validation, auth, CSRF, missing records, stock constraints and assistant responses | Run `pytest -q` before submission |
| Accessibility | Semantic headings and tables, form labels, accessible names for controls, status announcements, responsive styling and reduced-motion support | Manual keyboard/zoom review recommended in addition to automated tests |
| Problem statement alignment | Hospital operations persona, patient directory, appointment desk, supply stock thresholds, audit trail and deterministic database-grounded assistant | End-to-end workflow checks documented below |

## Tests

```bash
pip install -r requirements.txt
pytest -q
```

The suite covers authentication, login CSRF, redirect safety, patient search and creation, invalid input, missing records, inventory duplicate/negative-stock handling, appointment CSRF, malformed assistant JSON, security headers, and schema indexes. Run it in the same Python environment used for local development and include the actual result in the submission notes.

## Assumptions and limitations

- One administrator demo account is seeded for easy evaluation; role-based permissions and account management are not implemented.
- All patient names and contact numbers in seed data are fictional examples.
- Appointment records are administrative and do not check clinician calendars, room capacity, or clinical urgency.
- Admission count is a count of records marked `Admitted`, not a live bed-occupancy system.
- The assistant is deterministic and local; it does not call an external LLM or send data to third parties.
- No billing, prescriptions, clinical notes, diagnostic support, lab systems, file uploads, or integrations are included.
- This prototype is not designed for real patient data or production deployment.

## Repository constraints for challenge submission

- Keep the repository public and use only one branch (for example, `main`).
- Do not commit `medflow.db`, `.env`, credentials, patient data, or environment folders.
- The source project is intentionally small; verify the repository remains under the challenge's 10 MB limit before submitting.

## Deployment note: Vercel and persistence

The Vercel SQLite path under `/tmp` is only a temporary demonstration workaround. Serverless instances may be recycled or isolated, so data is **not guaranteed to persist**. Do not store real patient information. For reliable multi-instance deployment, migrate the database layer to managed PostgreSQL, add connection management and migrations, and configure the provider's connection string as a secret environment variable. `SECRET_KEY` must be a stable secret value in Vercel (the key name is `SECRET_KEY`; the random generated string belongs in the Value field).

## Remaining limitations / roadmap

1. Replace the single seeded administrator with managed accounts and least-privilege roles (reception, clinician, inventory manager).
2. Migrate to persistent PostgreSQL before relying on deployed writes; add migration and backup/restore procedures.
3. Add appointment conflict detection and inventory purchase-request approvals.
4. Add rate limiting, operational monitoring, dependency scanning, and a privacy/security review before any real-world use.
