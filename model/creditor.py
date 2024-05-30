import re

from pydantic import BaseModel, field_validator


class Creditor(BaseModel):
    name: str

    @field_validator('name', mode="before")
    def parse_timestamp(cls, value):
        if isinstance(value, str):
            return re.sub(r'\s+', ' ', value).lower()
        return value
