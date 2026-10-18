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

## Tests

```bash
pytest -q
```

Tests cover authentication gating, dashboard access, patient search, CSRF rejection, and assistant inventory answers.

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

## Suggested future improvements

1. Add least-privilege roles (reception, clinician, inventory manager) and stronger account provisioning.
2. Add audit log viewer, pagination, export controls, and explicit data-retention behavior.
3. Add appointment conflict detection and inventory purchase-request approval flow.
4. Add deployment hardening, rate limiting, security headers, backups, and security/privacy testing.
