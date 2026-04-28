from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Primitive validators
# ---------------------------------------------------------------------------

def _is_name(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    return bool(re.fullmatch(r"[A-Za-z\s'\-]+", value))


def _to_title_case(value: str) -> str:
    return value.strip().title()


def _is_ssn_last4(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"\d{4}", value))


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _is_18_plus(dob: date) -> bool:
    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return age >= 18


def _is_valid_email(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value))


def _digits_only(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\D", "", value)


# ---------------------------------------------------------------------------
# Field-level rule helpers
# ---------------------------------------------------------------------------

def _check_name(field: str, value: Any, errors: list[str], warnings: list[str]) -> None:
    if value is None:
        return
    if not _is_name(value):
        errors.append(f"{field}: must contain only letters, spaces, hyphens, or apostrophes (got {value!r})")
    elif value != _to_title_case(value):
        warnings.append(f"{field}: not in title case (got {value!r})")


def _check_ssn_last4(field: str, value: Any, errors: list[str]) -> None:
    if value is None:
        return
    if not _is_ssn_last4(value):
        errors.append(f"{field}: must be exactly 4 digits (got {value!r})")


def _check_date(field: str, value: Any, errors: list[str]) -> date | None:
    if value is None:
        return None
    parsed = _parse_date(value)
    if parsed is None:
        errors.append(f"{field}: not a recognisable date (got {value!r})")
    return parsed


def _check_dob(field: str, value: Any, errors: list[str]) -> None:
    parsed = _check_date(field, value, errors)
    if parsed is None:
        return
    if parsed >= date.today():
        errors.append(f"{field}: date of birth cannot be in the future")
        return
    if not _is_18_plus(parsed):
        errors.append(f"{field}: applicant must be at least 18 years old")


def _check_positive_amount(field: str, value: Any, max_value: float,
                            errors: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, (int, float)) or value <= 0:
        errors.append(f"{field}: must be a positive number (got {value!r})")
        return
    if value > max_value:
        errors.append(
            f"{field}: exceeds maximum allowed value of ${max_value:,.0f} (got ${value:,.2f})"
        )


def _check_email(field: str, value: Any, errors: list[str]) -> None:
    if value is None:
        return
    if not _is_valid_email(value):
        errors.append(f"{field}: invalid email format (got {value!r})")


def _check_phone(field: str, value: Any, errors: list[str]) -> None:
    if value is None:
        return
    digits = _digits_only(value)
    if len(digits) != 10:
        errors.append(
            f"{field}: must contain exactly 10 digits when stripped of formatting "
            f"(got {len(digits)} digits from {value!r})"
        )


# ---------------------------------------------------------------------------
# Per-form-type validators
# ---------------------------------------------------------------------------

def _validate_address(prefix: str, addr: Any, errors: list[str]) -> None:
    if not isinstance(addr, dict):
        errors.append(f"{prefix}: address must be an object")
        return
    for sub in ("street", "city", "state", "zip_code"):
        if not addr.get(sub):
            errors.append(f"{prefix}.{sub}: required")


def _validate_loan_application(data: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    _check_name("applicant_name", data.get("applicant_name"), errors, warnings)
    _check_ssn_last4("ssn_last4", data.get("ssn_last4"), errors)
    _check_dob("date_of_birth", data.get("date_of_birth"), errors)
    _validate_address("address", data.get("address"), errors)
    _check_positive_amount("annual_income", data.get("annual_income"), 10_000_000, errors)
    _check_positive_amount("loan_amount_requested", data.get("loan_amount_requested"),
                           2_000_000, errors)

    co = data.get("co_applicant")
    if co and isinstance(co, dict):
        _check_name("co_applicant.name", co.get("name"), errors, warnings)
        _check_ssn_last4("co_applicant.ssn_last4", co.get("ssn_last4"), errors)
        _check_dob("co_applicant.date_of_birth", co.get("date_of_birth"), errors)
        _check_positive_amount("co_applicant.annual_income", co.get("annual_income"),
                               10_000_000, errors)

    return errors, warnings


def _validate_membership_application(data: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    _check_name("first_name", data.get("first_name"), errors, warnings)
    _check_name("last_name", data.get("last_name"), errors, warnings)
    _check_ssn_last4("ssn_last4", data.get("ssn_last4"), errors)
    _check_dob("date_of_birth", data.get("date_of_birth"), errors)
    _validate_address("address", data.get("address"), errors)
    _check_phone("phone", data.get("phone"), errors)
    _check_email("email", data.get("email"), errors)
    _check_positive_amount("initial_deposit", data.get("initial_deposit"), 10_000_000, errors)

    return errors, warnings


def _validate_beneficiary_designation(data: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    _check_name("member_name", data.get("member_name"), errors, warnings)

    beneficiaries = data.get("beneficiaries") or []
    if not beneficiaries:
        errors.append("beneficiaries: at least one beneficiary is required")
    else:
        total = 0.0
        for i, b in enumerate(beneficiaries):
            if not isinstance(b, dict):
                errors.append(f"beneficiaries[{i}]: must be an object")
                continue
            _check_name(f"beneficiaries[{i}].name", b.get("name"), errors, warnings)
            _check_date(f"beneficiaries[{i}].date_of_birth", b.get("date_of_birth"), errors)
            pct = b.get("percentage")
            if pct is None:
                errors.append(f"beneficiaries[{i}].percentage: required")
            elif not isinstance(pct, (int, float)) or pct < 0 or pct > 100:
                errors.append(
                    f"beneficiaries[{i}].percentage: must be between 0 and 100 (got {pct!r})"
                )
            else:
                total += pct

        if beneficiaries and abs(total - 100.0) > 0.01:
            errors.append(
                f"beneficiaries: percentages must sum to exactly 100% (sum is {total:.2f}%)"
            )

    return errors, warnings


def _validate_change_of_address(data: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    _check_name("member_name", data.get("member_name"), errors, warnings)
    _validate_address("old_address", data.get("old_address"), errors)
    _validate_address("new_address", data.get("new_address"), errors)

    old = data.get("old_address") or {}
    new = data.get("new_address") or {}
    if (isinstance(old, dict) and isinstance(new, dict)
            and old.get("street") and old == new):
        warnings.append("new_address is identical to old_address")

    _check_date("effective_date", data.get("effective_date"), errors)

    return errors, warnings


_VALIDATORS = {
    "loan_application": _validate_loan_application,
    "membership_application": _validate_membership_application,
    "beneficiary_designation": _validate_beneficiary_designation,
    "change_of_address": _validate_change_of_address,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_extraction(form_type: str, data: dict) -> dict:
    validator = _VALIDATORS.get(form_type)
    if validator is None:
        return {
            "is_valid": False,
            "errors": [f"Unknown form type: {form_type!r}"],
            "warnings": [],
        }

    errors, warnings = validator(data)
    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
