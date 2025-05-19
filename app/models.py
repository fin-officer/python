from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Enumy dla statusów i analizy
class EmailStatus(str, Enum):
    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    REPLIED = "REPLIED"
    ERROR = "ERROR"


class Sentiment(str, Enum):
    VERY_NEGATIVE = "VERY_NEGATIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    POSITIVE = "POSITIVE"
    VERY_POSITIVE = "VERY_POSITIVE"


class Urgency(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Formality(str, Enum):
    VERY_INFORMAL = "VERY_INFORMAL"
    INFORMAL = "INFORMAL"
    NEUTRAL = "NEUTRAL"
    FORMAL = "FORMAL"
    VERY_FORMAL = "VERY_FORMAL"


class Emotion(str, Enum):
    ANGER = "ANGER"
    FEAR = "FEAR"
    HAPPINESS = "HAPPINESS"
    SADNESS = "SADNESS"
    SURPRISE = "SURPRISE"
    DISGUST = "DISGUST"
    NEUTRAL = "NEUTRAL"


# Modele dla email
class EmailSchema(BaseModel):
    from_email: EmailStr
    to_email: EmailStr
    subject: Optional[str] = None
    content: str
    received_date: Optional[str] = None
    id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "from_email": "user@example.com",
                "to_email": "service@example.com",
                "subject": "Zapytanie o produkt",
                "content": "Dzień dobry,\n\nChciałbym zapytać o dostępność produktu XYZ.\n\nPozdrawiam,\nJan Kowalski"
            }
        }


class EmailAttachment(BaseModel):
    filename: str
    content_type: str
    data: bytes


class EmailResponse(BaseModel):
    id: int
    status: str
    message: str


# Modele dla analizy tonu wiadomości
class ToneAnalysis(BaseModel):
    sentiment: Sentiment
    emotions: Dict[Emotion, float]
    urgency: Urgency
    formality: Formality
    top_topics: List[str] = Field(default_factory=list)
    summary_text: str


# Modele dla szablonów
class TemplateSchema(BaseModel):
    key: str
    content: str
    preview: Optional[str] = None


class TemplateResponse(BaseModel):
    key: str
    content: str


class TemplateListResponse(BaseModel):
    templates: List[TemplateSchema]


# Model dla bazy danych
class EmailDB(BaseModel):
    id: Optional[int] = None
    from_email: str
    to_email: str
    subject: Optional[str] = None
    content: str
    received_date: datetime = Field(default_factory=datetime.now)
    processed_date: Optional[datetime] = None
    tone_analysis: Optional[str] = None  # JSON jako string
    status: EmailStatus = EmailStatus.RECEIVED

    class Config:
        from_attributes = True