from pydantic import BaseModel, Field, EmailStr
from typing import Optional

class LeadInput(BaseModel):
    name: str = Field(..., min_length=2,description="Name of the lead")
    email: EmailStr = Field(..., description="Email address of the lead")
    phone: Optional[str] = Field(None, description="Phone number of the lead")
    message: str = Field(..., min_length=5, description="Initial inquiry or Message from the lead")

class ProcessedLead(BaseModel):
    name:str
    email: EmailStr
    phone: Optional[str]
    message: str
    category: str
    summary: str
    draft_response: str

