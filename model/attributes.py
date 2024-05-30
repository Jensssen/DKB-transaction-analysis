from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from model.amount import Amount
from model.creditor import Creditor


class Attributes(BaseModel):
    bookingDate: datetime
    description: Optional[str] = "-"
    transactionType: str
    status: str
    amount: Amount
    creditor: Creditor

    @field_validator('bookingDate', mode="before")
    def parse_timestamp(cls, value):
        if isinstance(value, str):
            return datetime.strptime(value, '%Y-%m-%d')
        return value
