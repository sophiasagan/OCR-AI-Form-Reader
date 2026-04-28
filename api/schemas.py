from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class Address(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str


class CoApplicant(BaseModel):
    name: str
    ssn_last4: str = Field(min_length=4, max_length=4)
    date_of_birth: str
    employer: str
    annual_income: float


class LoanApplication(BaseModel):
    form_type: Literal["loan_application"] = "loan_application"
    applicant_name: str
    ssn_last4: str = Field(min_length=4, max_length=4)
    date_of_birth: str
    address: Address
    employer: str
    annual_income: float
    loan_amount_requested: float
    loan_purpose: str
    co_applicant: Optional[CoApplicant] = None
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    missing_required_fields: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)


class MembershipApplication(BaseModel):
    form_type: Literal["membership_application"] = "membership_application"
    first_name: str
    last_name: str
    ssn_last4: str = Field(min_length=4, max_length=4)
    date_of_birth: str
    address: Address
    phone: str
    email: str
    id_type: str
    id_number: str
    initial_deposit: float
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    missing_required_fields: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)


class Beneficiary(BaseModel):
    name: str
    relationship: str
    date_of_birth: str
    percentage: float = Field(ge=0.0, le=100.0)


class BeneficiaryDesignation(BaseModel):
    form_type: Literal["beneficiary_designation"] = "beneficiary_designation"
    member_name: str
    account_number: str
    beneficiaries: list[Beneficiary]
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    missing_required_fields: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)


class ChangeOfAddress(BaseModel):
    form_type: Literal["change_of_address"] = "change_of_address"
    member_name: str
    account_number: str
    old_address: Address
    new_address: Address
    effective_date: str
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    missing_required_fields: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)


FormSchema = LoanApplication | MembershipApplication | BeneficiaryDesignation | ChangeOfAddress
