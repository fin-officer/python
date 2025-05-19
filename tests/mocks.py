#!/usr/bin/env python3

"""
Mock classes for testing
"""
from enum import Enum
from typing import Dict, List, Optional


class Sentiment(str, Enum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"


class Emotion(str, Enum):
    HAPPINESS = "HAPPINESS"
    SADNESS = "SADNESS"
    ANGER = "ANGER"
    FEAR = "FEAR"
    SURPRISE = "SURPRISE"
    NEUTRAL = "NEUTRAL"


class Urgency(str, Enum):
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


class Formality(str, Enum):
    FORMAL = "FORMAL"
    NEUTRAL = "NEUTRAL"
    INFORMAL = "INFORMAL"


class ToneAnalysis:
    def __init__(
        self,
        sentiment: Sentiment = Sentiment.NEUTRAL,
        emotions: Dict[Emotion, float] = None,
        urgency: Urgency = Urgency.NORMAL,
        formality: Formality = Formality.NEUTRAL,
        top_topics: List[str] = None,
        summary_text: str = "",
    ):
        self.sentiment = sentiment
        self.emotions = emotions or {}
        self.urgency = urgency
        self.formality = formality
        self.top_topics = top_topics or []
        self.summary_text = summary_text


class EmailSchema:
    def __init__(
        self,
        id: int = None,
        from_email: str = "",
        to_email: str = "",
        subject: str = "",
        content: str = "",
        received_date: str = None,
    ):
        self.id = id
        self.from_email = from_email
        self.to_email = to_email
        self.subject = subject
        self.content = content
        self.received_date = received_date


class LlmService:
    def __init__(self):
        self.api_url = "http://localhost:11434"
        self.model = "llama2"

    async def generate_auto_reply(
        self, email_content: str, sender_name: str, email_history: list = None
    ) -> str:
        return f"Auto-reply to {sender_name}: Thank you for your message."

    def _create_mcp_context(
        self, email_content: str, sender_name: str, email_history: list = None
    ) -> dict:
        return {
            "context": {
                "service": "Usługi finansowe i księgowe",
                "sender": {"name": sender_name},
                "email": {"content": email_content},
            }
        }

    async def _call_llm_api_with_mcp(self, mcp_context: dict) -> str:
        return "Mock response from LLM API"

    def _create_default_reply(self, sender_name: str) -> str:
        return f"Dziękujemy za wiadomość, {sender_name}."
