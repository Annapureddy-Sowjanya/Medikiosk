# MediKiosk Full-Stack Upgrade (Development Prototype)

React + Vite frontend, FastAPI backend, MySQL database, OCR for image/text-PDF documents, multilingual browser voice input, optional OpenAI-generated clinical documentation drafts, staff JWT login, patient timeline, OPD queue, PDF export, and a local FHIR-shaped JSON export.

> **Clinical safety and scope:** MediKiosk is an educational prototype, not a medical device or production hospital system. It does not diagnose or recommend treatment. Summaries are drafts and require a qualified physician to verify and review them. OCR can be wrong. Rule-based red-flag wording is not a reliable emergency detector. Do not upload real patient data. The FHIR-shaped export is not a live ABDM integration; no ABDM sandbox/production credentials, consent artefacts, or exchange are connected.

## Features included

- Existing patient registration, consent/revocation, adaptive questions, clinical history, document upload, summary draft and physician review.
- MySQL through SQLAlchemy; database schema is created automatically on first start. Set `DATABASE_URL` in `backend/.env`.
- Image OCR via Tesseract and text extraction from PDFs. Scanned PDF OCR additionally needs Poppler and `pdf2image`.
- Voice input in supported browsers for English, Telugu, Hindi, Tamil, Kannada, Malayalam, Bengali and Marathi. Browser support and network behaviour vary; typing remains available.
- Optional OpenAI summary provider; without a key, deterministic template fallback works offline.
- JWT staff authentication. The **first registered account becomes admin**; after that, public registration is closed. Admins can create staff accounts using `POST /api/auth/users` in Swagger.
- Timeline, staff dashboard, OPD queue updates and physician-review PDF export.
- Local FHIR R4-shaped bundle export at `GET /api/sessions/{session_id}/fhir`, accessible to signed-in physicians/admins. This is export preparation only, not an ABDM integration.

## Requirements

- Windows 10/11, VS Code
- Python 3.10+ (Python 3.11 recommended)
- Node.js 20+ LTS
- MySQL Server 8+ (a MySQL-compatible local server)
- Tesseract OCR for image OCR. For scanned PDFs, also install Poppler.

## A. Open the project in VS Code

1. Extract the ZIP to a simple path, for example `C:\MediKiosk`.
2. In VS Code choose **File → Open Folder** and select `C:\MediKiosk`.
3. Open **Terminal → New Terminal**. Commands below assume the folder is `C:\MediKiosk`. If you extracted elsewhere, change the `cd` paths.

## B. Configure MySQL

1. Start MySQL Server.
2. Open MySQL Workbench or the MySQL command-line client and run the SQL in `backend/create_database.sql`. This creates database `medikiosk` and a development user. Change the example password before using it.
3. Copy `backend/.env.example` to `backend/.env`.
4. Edit `backend/.env` and make the `DATABASE_URL` credentials match the MySQL user/password you created. Example format:

   `DATABASE_URL=mysql+pymysql://medikiosk:YourPassword@127.0.0.1:3306/medikiosk`

   If your password contains URL-special characters, URL-encode them or use a simple development-only password. Never commit `.env` to Git.
5. Replace `JWT_SECRET` with a long random secret. This is required before deployment; the example value is only a placeholder.

The app creates tables when the backend starts. If you have old SQLite demo data, it is **not automatically migrated** into MySQL. Keep the original ZIP/database as a backup.

## C. Install Tesseract OCR (Windows)

1. Install the Windows Tesseract OCR package from a trusted official/project distribution.
2. Make sure `tesseract.exe` is on PATH. A common install location is `C:\Program Files\Tesseract-OCR\tesseract.exe`.
3. Restart VS Code after changing PATH.
4. If OCR reports that Tesseract is not available, add that folder to Windows Environment Variables → Path, then open a new terminal and run `tesseract --version`.
5. Text-based PDFs can be read without Tesseract. Scanned PDFs require Poppler and `pdf2image`; if those are not installed the app tells you that OCR setup is needed.

## D. Start the FastAPI backend

In VS Code terminal:

```powershell
cd C:\MediKiosk\backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

If `.env` already exists, do not overwrite it with the copy command. Edit it first to match your MySQL setup. If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate again.

Start the server:

```powershell
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` to test the API. Keep this terminal running. If startup fails, verify MySQL is running and the `DATABASE_URL` password/database are correct.

## E. Start the React frontend

Open a **second** VS Code terminal:

```powershell
cd C:\MediKiosk\frontend
npm install
npm run dev
```

Open the URL Vite prints, usually `http://localhost:5173`.

## F. First staff login

1. Open **Staff login** in the app or go to `http://localhost:5173/login`.
2. Choose **First time? Create account** and create the first account with a strong password of at least 12 characters. This first account becomes the admin.
3. Subsequent public registrations are blocked. To create more accounts, sign in as admin, open `http://127.0.0.1:8000/docs`, authorize with the bearer token (login first using `POST /api/auth/login`), and use `POST /api/auth/users` with `email`, `full_name`, a password of at least 12 characters, and role `physician` or `staff`.
4. Sign in through the app. Staff dashboard, queue and physician review endpoints require the appropriate role.

## G. Optional AI summary provider

The app works without a paid API key using a structured template. To enable OpenAI summaries, set in `backend/.env`:

```dotenv
AI_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

Restart FastAPI after changing `.env`. API usage may incur charges. Do not send identifiable patient data to an external provider. For a classroom demo, use fictional test data. If the provider call fails, the backend falls back to a template.

## H. Test the full workflow

1. Start backend and frontend.
2. Click **Start consultation** and enter fictional patient details. The app assigns a queue number.
3. Give consent on the consent page.
4. Enter chief complaint, HPI, medicines, allergies and other history. Use the microphone where your browser supports the selected language, or type manually.
5. Upload a clear JPG/PNG image or a text-based PDF. Review the extracted text carefully; OCR is not guaranteed accurate.
6. Save answers and create a summary draft.
7. Sign in as a physician/admin and open Physician review. Edit the draft and select an appropriate review status. The summary must remain a draft until a qualified clinician has reviewed it.
8. From the summary screen, download a PDF. From the dashboard, open a session timeline. From Queue, update the operational queue status.
9. To test the local FHIR-shaped export, call `GET /api/sessions/{session_id}/fhir` in Swagger while signed in as admin/physician. It does not send data to ABDM.

## API highlights

- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, admin-only `POST /api/auth/users`
- `POST /api/patients`, `POST /api/sessions/{id}/consent`, `POST /api/sessions/{id}/answers`
- `POST /api/sessions/{id}/documents`, `POST /api/sessions/{id}/summary`
- Staff: `GET /api/dashboard`, `GET /api/queue`, `PUT /api/queue/{entry_id}`, `PUT /api/sessions/{id}/review`
- Staff: `GET /api/sessions/{id}/timeline`, `GET /api/sessions/{id}/summary.pdf`, `GET /api/sessions/{id}/fhir`
- `GET /api/integrations/status`

## Important limitations before any real deployment

This is not production-ready. Before using real patient information, add security and clinical governance review, managed authentication/SSO, patient-session authorization, rate limiting, HTTPS, encryption and key management, malware scanning, secure object storage, retention/deletion policy, database backups, migrations, comprehensive audit logging, clinical validation, accessibility testing, and legal/privacy review. ABDM integration requires the appropriate official onboarding, sandbox testing, consent workflows and credentials; the current endpoint is not a live connection.
