from __future__ import annotations

import logging
from typing import Any

from dotenv import load_dotenv
load_dotenv()  # must run before any api.* import creates the Anthropic client

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.extractor import _MODEL, extract_form
from api.schemas import (
    BeneficiaryDesignation,
    ChangeOfAddress,
    LoanApplication,
    MembershipApplication,
)
from api.validator import validate_extraction

logger = logging.getLogger(__name__)

app = FastAPI(
    title="CU Form Reader",
    description="OCR + AI extraction for credit union forms",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB

_SUPPORTED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/webp",
}

_FORM_TYPE_SCHEMAS: dict[str, type] = {
    "loan_application": LoanApplication,
    "membership_application": MembershipApplication,
    "beneficiary_designation": BeneficiaryDesignation,
    "change_of_address": ChangeOfAddress,
}


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class ValidationResult(BaseModel):
    is_valid: bool
    errors: list[str]
    warnings: list[str]


class ExtractionResult(BaseModel):
    form_type: str
    extracted_data: dict[str, Any] | None
    validation: ValidationResult
    raw_claude_response: str
    processing_time_ms: int


class FormTypeInfo(BaseModel):
    form_type: str
    fields: list[dict[str, Any]]


class HealthResponse(BaseModel):
    status: str
    claude_model: str
    supported_form_types: list[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/extract", response_model=ExtractionResult)
async def extract(file: UploadFile = File(...)) -> ExtractionResult:
    if file.content_type not in _SUPPORTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type: {file.content_type!r}. "
                f"Accepted: {sorted(_SUPPORTED_CONTENT_TYPES)}"
            ),
        )

    file_bytes = await file.read()

    if len(file_bytes) > _MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds 10 MB limit ({len(file_bytes) / 1_048_576:.1f} MB received)",
        )

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        result = extract_form(file_bytes, file.filename or "upload")
    except Exception as exc:
        logger.exception("Extraction failed for %s", file.filename)
        raise HTTPException(status_code=500, detail=f"Extraction error: {exc}") from exc

    form_type = result["form_type"]
    extracted_data = result.get("extracted_data")

    if form_type == "unknown" or extracted_data is None:
        validation = ValidationResult(
            is_valid=False,
            errors=["Could not identify form type from the uploaded document"],
            warnings=[],
        )
    else:
        raw_validation = validate_extraction(form_type, extracted_data)
        validation = ValidationResult(**raw_validation)
        if extracted_data:
            extracted_data["validation_errors"] = validation.errors

    return ExtractionResult(
        form_type=form_type,
        extracted_data=extracted_data,
        validation=validation,
        raw_claude_response=result["raw_claude_response"],
        processing_time_ms=result["processing_time_ms"],
    )


@app.get("/form-types", response_model=list[FormTypeInfo])
def get_form_types() -> list[FormTypeInfo]:
    result = []
    for form_type, schema_cls in _FORM_TYPE_SCHEMAS.items():
        fields = []
        for name, info in schema_cls.model_fields.items():
            annotation = info.annotation
            fields.append(
                {
                    "name": name,
                    "type": str(annotation),
                    "required": info.is_required(),
                    "description": info.description or "",
                }
            )
        result.append(FormTypeInfo(form_type=form_type, fields=fields))
    return result


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        claude_model=_MODEL,
        supported_form_types=list(_FORM_TYPE_SCHEMAS.keys()),
    )
