from pydantic import BaseModel, Field


class DuplicateCheckRequest(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=20, max_length=1000)
