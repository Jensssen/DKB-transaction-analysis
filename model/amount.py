from pydantic import BaseModel, field_validator


class Amount(BaseModel):
    currencyCode: str
    value: float

    @field_validator('value', mode="before")
    def parse_timestamp(cls, value):
        if isinstance(value, str):
            return float(value)
        return value
