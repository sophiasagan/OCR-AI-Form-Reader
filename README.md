# CU Form Reader

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)
![Claude](https://img.shields.io/badge/Claude-claude--opus--4--7-D97757?style=flat&logo=anthropic&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-06B6D4?style=flat&logo=tailwindcss&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

AI-powered OCR for credit union forms. Upload a scanned PDF or image — Claude vision classifies the form type, extracts every field into validated JSON, and surfaces confidence scores and missing fields in a side-by-side review UI.

---

## Demo

> **GIF placeholder** — replace this block with a screen recording once the app is running.
> Recommended tool: [ScreenToGif](https://www.screentogif.com/) (Windows) or [Kap](https://getkap.co/) (Mac).

```
[ demo.gif goes here ]
```

Suggested flow to record:
1. Drag a scanned loan application PDF onto the upload zone
2. Watch the progress bar while Claude processes
3. Show the extracted fields panel with section groupings and confidence badge
4. Click an edit icon and correct a field inline
5. Click "Export to CSV"

---

## Supported Form Types

| Form | Fields Extracted |
|---|---|
| Loan Application | Applicant name, DOB, SSN×4, address, employer, income, loan amount, purpose, co-applicant |
| Membership Application | Name, DOB, SSN×4, address, phone, email, ID type/number, initial deposit |
| Beneficiary Designation | Member name, account number, beneficiary list (name, relationship, DOB, %) |
| Change of Address | Member name, account number, old address, new address, effective date |

---

## Architecture

```
Browser
  │  multipart/form-data (≤ 10 MB)
  ▼
FastAPI  /extract
  │
  ├─ preprocessor.py
  │     pdf2image (Poppler) → PIL → contrast/sharpness enhance → base64
  │
  ├─ extractor.py  ── two Claude calls ──────────────────────────────────────┐
  │     Call 1 (32 tokens):  classify form type                              │
  │     Call 2 (1024 tokens): type-specific extraction prompt → JSON         │
  │     Hydrate Pydantic schema, average section confidence scores           │
  │     Mask account numbers before schema / logs                            │◄─ Claude API
  │                                                                          │  claude-opus-4-7
  ├─ validator.py                                                            │
  │     Business rules: name format, SSN digits, 18+ DOB,                   │
  │     loan ≤ $2M, beneficiary % = 100, email, phone (10 digits)           │
  │
  └─ ExtractionResult → JSON response
         form_type, extracted_data, validation, raw_claude_response,
         processing_time_ms

React (Vite + Tailwind)
  ├─ UploadZone    drag-and-drop, file validation, animated progress bar
  ├─ FormPreview   live PDF/image preview via object URL
  └─ ExtractedDataCard
        Header:  form type badge · confidence % · processing time
        Banners: validation errors (red) · warnings (amber) · low-conf flag
        Fields:  grouped by section · inline edit on click
        Footer:  Copy JSON · Export CSV · Clear
```

### Data flow

```
Upload → preprocess → classify → extract → validate → display
  10MB      PIL         32 tok    1024 tok   rules      React
  limit    enhance      Claude    Claude     engine     UI
```

### Security notes

- SSN last-4 only — full SSN never accepted, stored, or logged
- Account numbers masked to `****1234` before schema hydration
- Confidence < 0.7 on any field section → flagged for human review
- Max file size enforced both client-side (JS) and server-side (FastAPI)

---

## Getting Started

### Prerequisites

| Dependency | Install |
|---|---|
| Python 3.11+ | [python.org](https://python.org) |
| Node 18+ | [nodejs.org](https://nodejs.org) |
| Poppler | Windows: `winget install oschwartz10612.Poppler` · Linux: `apt install poppler-utils` · Mac: `brew install poppler` |
| Anthropic API key | [console.anthropic.com](https://console.anthropic.com) |

### Setup

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd cu_form_reader

# 2. Python deps
pip install -r requirements.txt

# 3. Environment variables
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY and (Windows only) POPPLER_PATH

# 4. Start the API
uvicorn api.main:app --reload --port 8000

# 5. Start the frontend (separate terminal)
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key |
| `POPPLER_PATH` | Windows only | Path to Poppler `bin/` folder, e.g. `C:\poppler\Library\bin` |

---

## Deployment

The frontend and backend deploy independently.

### Frontend → GitHub Pages

1. In your repo go to **Settings → Pages** and set Source to **GitHub Actions**.
2. Go to **Settings → Secrets and variables → Actions → Variables** and add:

   | Variable | Value |
   |---|---|
   | `VITE_API_URL` | Your deployed backend URL, e.g. `https://cu-form-reader.up.railway.app` |
   | `VITE_BASE_PATH` | `/your-repo-name/` (only needed for project pages, not a custom domain) |

3. Push to `main` — the [deploy workflow](.github/workflows/deploy.yml) builds `frontend/dist` and publishes it automatically.

### Backend → Railway (or any Python host)

```bash
# Railway CLI
railway login
railway init
railway up
```

Set the `ANTHROPIC_API_KEY` environment variable in the Railway dashboard. Poppler is available on Railway's Linux environment via `apt`; add a `nixpacks.toml` if you need to pin it:

```toml
# nixpacks.toml
[phases.setup]
aptPkgs = ["poppler-utils"]
```

Make sure the backend has CORS configured for your GitHub Pages domain. The `allow_origins=["*"]` in `api/main.py` covers this for now — tighten it to your Pages URL before going to production.

---

## API Reference

### `POST /extract`

Upload a form for extraction.

**Request:** `multipart/form-data` with a `file` field (PDF, JPG, PNG, TIFF, WEBP — max 10 MB)

**Response:**
```json
{
  "form_type": "loan_application",
  "extracted_data": {
    "applicant_name": "Jane Smith",
    "ssn_last4": "4321",
    "date_of_birth": "1985-03-22",
    "address": { "street": "123 Main St", "city": "Portland", "state": "OR", "zip_code": "97201" },
    "employer": "Acme Corp",
    "annual_income": 72000,
    "loan_amount_requested": 15000,
    "loan_purpose": "Home improvement",
    "co_applicant": null,
    "extraction_confidence": 0.91,
    "missing_required_fields": [],
    "validation_errors": []
  },
  "validation": {
    "is_valid": true,
    "errors": [],
    "warnings": []
  },
  "raw_claude_response": "...",
  "processing_time_ms": 4821
}
```

### `GET /form-types`

Returns supported form types with their full field schemas.

### `GET /health`

```json
{ "status": "ok", "claude_model": "claude-opus-4-7", "supported_form_types": ["loan_application", "membership_application", "beneficiary_designation", "change_of_address"] }
```

---

## Project Structure

```
cu_form_reader/
├── api/
│   ├── main.py          FastAPI app — /extract, /form-types, /health
│   ├── schemas.py       Pydantic models per form type
│   ├── extractor.py     Claude vision — classify then extract
│   ├── validator.py     Business rule validation
│   └── preprocessor.py  PDF → image, contrast enhancement
├── frontend/
│   └── src/
│       ├── App.jsx               Two-panel layout
│       ├── api.js                Fetch wrapper
│       └── components/
│           ├── UploadZone.jsx    Drag-and-drop + progress bar
│           ├── FormPreview.jsx   Live file preview
│           └── ExtractedDataCard.jsx  Field review + edit + export
├── forms/               Sample scanned forms for testing
├── requirements.txt
├── .env.example
└── README.md
```

---

## License

MIT
