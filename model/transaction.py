from datetime import datetime

from pydantic import BaseModel, field_validator

from model.attributes import Attributes


class Transaction(BaseModel):
    id: datetime
    attributes: Attributes

    @field_validator('id', mode="before")
    def parse_timestamp(cls, value):
        if isinstance(value, str):
            return datetime.strptime(value, '%Y-%m-%d-%H.%M.%S.%f')
        return value
