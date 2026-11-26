from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

CADENCES = {"weekly", "biweekly", "monthly", "quarterly", "annually", "one_off"}


class ContributionAgreementCreate(BaseModel):
    member_id: UUID
    name: str = Field(min_length=1, max_length=200)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    cadence: str = "monthly"
    due_day: int | None = Field(default=None, ge=1, le=31)
    start_date: date
    end_date: date | None = None
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_dates_and_cadence(self):
        if self.cadence not in CADENCES:
            raise ValueError("Unsupported contribution cadence.")
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("End date cannot be before start date.")
        if self.cadence == "monthly" and self.due_day is None:
            raise ValueError("Monthly agreements require a due day.")
        return self


class ContributionAgreementUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=2)
    cadence: str | None = None
    due_day: int | None = Field(default=None, ge=1, le=31)
    end_date: date | None = None
    status: str | None = None
    notes: str | None = Field(default=None, max_length=500)


class ContributionAgreementOut(BaseModel):
    id: UUID
    household_id: UUID
    member_id: UUID
    name: str
    amount: Decimal
    currency: str
    cadence: str
    due_day: int | None
    start_date: date
    end_date: date | None
    status: str
    notes: str | None
    model_config = {"from_attributes": True}


class ContributionRecordCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    contributed_on: date
    transaction_id: UUID | None = None
    note: str | None = Field(default=None, max_length=500)


class ContributionRecordOut(BaseModel):
    id: UUID
    household_id: UUID
    agreement_id: UUID
    member_id: UUID
    amount: Decimal
    currency: str
    contributed_on: date
    transaction_id: UUID | None
    note: str | None
    model_config = {"from_attributes": True}
