from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import anthropic

from api.preprocessor import prepare_image
from api.schemas import (
    BeneficiaryDesignation,
    ChangeOfAddress,
    FormSchema,
    LoanApplication,
    MembershipApplication,
)

logger = logging.getLogger(__name__)

_MODEL = "claude-opus-4-7"
_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client

_VALID_FORM_TYPES = {
    "loan_application",
    "membership_application",
    "beneficiary_designation",
    "change_of_address",
}

# ---------------------------------------------------------------------------
# Classification prompt
# ---------------------------------------------------------------------------

_CLASSIFY_PROMPT = (
    "Identify which type of credit union form this is. "
    "Reply with exactly one of: "
    "loan_application, membership_application, beneficiary_designation, "
    "change_of_address, unknown"
)

# ---------------------------------------------------------------------------
# Per-type extraction prompts
# ---------------------------------------------------------------------------

_EXTRACTION_PROMPTS: dict[str, str] = {
    "loan_application": """
Extract all fields from this loan application form and return a single JSON object.

Required fields:
- applicant_name (string)
- ssn_last4 (string, last 4 digits of SSN only — never the full number)
- date_of_birth (string, ISO 8601 YYYY-MM-DD if possible)
- address (object: street, city, state, zip_code)
- employer (string)
- annual_income (number)
- loan_amount_requested (number)
- loan_purpose (string)
- co_applicant (object or null): if present include name, ssn_last4, date_of_birth, employer, annual_income

Confidence guidance:
- "section_confidence": estimate 0.0–1.0 per logical section
  (applicant_info, financial_info, co_applicant if present)

Rules:
- Use null for any field you cannot read clearly
- Do not fabricate values
- Numbers must be bare numerics (no $ or commas)

Return ONLY valid JSON matching this shape:
{
  "applicant_name": "...",
  "ssn_last4": "...",
  "date_of_birth": "...",
  "address": {"street": "...", "city": "...", "state": "...", "zip_code": "..."},
  "employer": "...",
  "annual_income": 0,
  "loan_amount_requested": 0,
  "loan_purpose": "...",
  "co_applicant": null,
  "section_confidence": {"applicant_info": 0.9, "financial_info": 0.8}
}
""",

    "membership_application": """
Extract all fields from this membership application form and return a single JSON object.

Required fields:
- first_name (string)
- last_name (string)
- ssn_last4 (string, last 4 digits only)
- date_of_birth (string, ISO 8601 YYYY-MM-DD if possible)
- address (object: street, city, state, zip_code)
- phone (string)
- email (string)
- id_type (string, e.g. "Driver's License", "Passport")
- id_number (string)
- initial_deposit (number)

Confidence guidance:
- "section_confidence": estimate 0.0–1.0 per section
  (personal_info, contact_info, identification, financial)

Rules:
- Use null for any field you cannot read clearly
- Do not fabricate values
- Numbers must be bare numerics

Return ONLY valid JSON matching this shape:
{
  "first_name": "...",
  "last_name": "...",
  "ssn_last4": "...",
  "date_of_birth": "...",
  "address": {"street": "...", "city": "...", "state": "...", "zip_code": "..."},
  "phone": "...",
  "email": "...",
  "id_type": "...",
  "id_number": "...",
  "initial_deposit": 0,
  "section_confidence": {"personal_info": 0.9, "contact_info": 0.85, "identification": 0.9, "financial": 0.8}
}
""",

    "beneficiary_designation": """
Extract all fields from this beneficiary designation form and return a single JSON object.

Required fields:
- member_name (string)
- account_number (string — mask all but last 4 digits with *)
- beneficiaries (array of objects, each with):
    - name (string)
    - relationship (string)
    - date_of_birth (string, ISO 8601 YYYY-MM-DD if possible)
    - percentage (number 0–100)

Confidence guidance:
- "section_confidence": estimate 0.0–1.0 per section
  (member_info, beneficiary_list)

Rules:
- Use null for any field you cannot read clearly
- Do not fabricate values
- Percentage must be a bare number (no % symbol)

Return ONLY valid JSON matching this shape:
{
  "member_name": "...",
  "account_number": "...",
  "beneficiaries": [
    {"name": "...", "relationship": "...", "date_of_birth": "...", "percentage": 100}
  ],
  "section_confidence": {"member_info": 0.95, "beneficiary_list": 0.85}
}
""",

    "change_of_address": """
Extract all fields from this change of address form and return a single JSON object.

Required fields:
- member_name (string)
- account_number (string — mask all but last 4 digits with *)
- old_address (object: street, city, state, zip_code)
- new_address (object: street, city, state, zip_code)
- effective_date (string, ISO 8601 YYYY-MM-DD if possible)

Confidence guidance:
- "section_confidence": estimate 0.0–1.0 per section
  (member_info, old_address, new_address)

Rules:
- Use null for any field you cannot read clearly
- Do not fabricate values

Return ONLY valid JSON matching this shape:
{
  "member_name": "...",
  "account_number": "...",
  "old_address": {"street": "...", "city": "...", "state": "...", "zip_code": "..."},
  "new_address": {"street": "...", "city": "...", "state": "...", "zip_code": "..."},
  "effective_date": "...",
  "section_confidence": {"member_info": 0.95, "old_address": 0.9, "new_address": 0.9}
}
""",
}

_SCHEMA_MAP: dict[str, type[FormSchema]] = {  # type: ignore[valid-type]
    "loan_application": LoanApplication,
    "membership_application": MembershipApplication,
    "beneficiary_designation": BeneficiaryDesignation,
    "change_of_address": ChangeOfAddress,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _image_message(base64_data: str, media_type: str, prompt: str) -> list[dict]:
    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64_data,
                    },
                },
                {"type": "text", "text": prompt},
            ],
        }
    ]


def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of a Claude response string."""
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("No JSON object found in Claude response")
    return json.loads(match.group())


def _avg_section_confidence(data: dict) -> float:
    section_conf = data.get("section_confidence", {})
    if not section_conf:
        return 0.5
    values = [v for v in section_conf.values() if isinstance(v, (int, float))]
    return round(sum(values) / len(values), 4) if values else 0.5


def _collect_missing(data: dict, schema_cls: type) -> list[str]:
    missing = []
    for field_name, field_info in schema_cls.model_fields.items():
        if field_name in {"form_type", "extraction_confidence",
                          "missing_required_fields", "validation_errors"}:
            continue
        if field_info.is_required() and data.get(field_name) is None:
            missing.append(field_name)
    return missing


def _mask_account_number(value: str | None) -> str | None:
    if value and len(value) > 4:
        return "*" * (len(value) - 4) + value[-4:]
    return value


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_form(image_bytes: bytes, filename: str) -> dict[str, Any]:
    t_start = time.monotonic()

    base64_data, media_type = prepare_image(image_bytes, filename)

    # --- Step 1: classify ---
    classify_response = _get_client().messages.create(
        model=_MODEL,
        max_tokens=32,
        messages=_image_message(base64_data, media_type, _CLASSIFY_PROMPT),
    )
    raw_classify = classify_response.content[0].text.strip().lower()
    form_type = raw_classify if raw_classify in _VALID_FORM_TYPES else "unknown"

    if form_type == "unknown":
        processing_time_ms = round((time.monotonic() - t_start) * 1000)
        return {
            "form_type": "unknown",
            "extracted_data": None,
            "raw_claude_response": raw_classify,
            "processing_time_ms": processing_time_ms,
        }

    # --- Step 2: extract ---
    extraction_prompt = _EXTRACTION_PROMPTS[form_type]
    extract_response = _get_client().messages.create(
        model=_MODEL,
        max_tokens=1024,
        messages=_image_message(base64_data, media_type, extraction_prompt),
    )
    raw_extraction = extract_response.content[0].text

    # --- Step 3: parse + hydrate schema ---
    parsed = _extract_json(raw_extraction)

    # Mask sensitive values before they touch the schema or logs
    if "account_number" in parsed:
        parsed["account_number"] = _mask_account_number(parsed["account_number"])

    confidence = _avg_section_confidence(parsed)
    schema_cls = _SCHEMA_MAP[form_type]
    missing = _collect_missing(parsed, schema_cls)

    if confidence < 0.7:
        logger.warning(
            "Low confidence extraction (%.2f) for %s — flagged for human review",
            confidence,
            filename,
        )

    hydrated = schema_cls.model_validate(
        {
            **parsed,
            "form_type": form_type,
            "extraction_confidence": confidence,
            "missing_required_fields": missing,
            "validation_errors": [],
        }
    )

    processing_time_ms = round((time.monotonic() - t_start) * 1000)

    return {
        "form_type": form_type,
        "extracted_data": hydrated.model_dump(),
        "raw_claude_response": raw_extraction,
        "processing_time_ms": processing_time_ms,
    }
