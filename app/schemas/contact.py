from pydantic import BaseModel, EmailStr
from typing import Optional


class ContactForm(BaseModel):
    """Contact form schema"""
    name: str
    email: EmailStr
    company: Optional[str] = None
    subject: Optional[str] = None
    message: Optional[str] = None


class ContactResponse(BaseModel):
    """Contact response schema"""
    detail: str 