import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import aiohttp
from dotenv import load_dotenv
from app.models import Emotion, Formality, Sentiment, ToneAnalysis, Urgency

# Załaduj zmienne środowiskowe
load_dotenv()

logger = logging.getLogger("llm_service")


class LlmService:
    def __init__(self):
        self.api_url = os.getenv("LLM_API_URL", "http://localhost:11434")
        self.model = os.getenv("LLM_MODEL", "llama2")
        logger.info(f"Inicjalizacja LLM Service z URL: {self.api_url}, model: {self.model}")

    async def analyze_tone(self, content: str) -> ToneAnalysis:
        """
        Analizuje ton wiadomości email przy użyciu LLM.
        """
        if not content or content.strip() == "":
            logger.warning("Pusta treść wiadomości, zwracanie domyślnej analizy")
            return self._create_default_analysis()

        try:
            logger.info("Analizowanie tonu wiadomości...")

            # Tworzenie promptu dla modelu LLM
            prompt = self._create_analysis_prompt(content)

            # Wywołanie API modelu
            response = await self._call_llm_api(prompt)

            # Parsowanie odpowiedzi
            return self._parse_analysis_response(response)

        except Exception as e:
            logger.error(f"Błąd podczas analizy tonu: {str(e)}")
            return self._create_default_analysis()

    async def check_connection(self) -> bool:
        """
        Sprawdza połączenie z API modelu językowego.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/api/version") as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania połączenia z LLM API: {str(e)}")
            return False

    def _create_analysis_prompt(self, content: str) -> str:
        """
        Tworzy prompt dla modelu LLM do analizy tonu.
        """
        return f"""
        Przeanalizuj poniższą wiadomość email i podaj:
        1. Ogólny sentyment (VERY_NEGATIVE, NEGATIVE, NEUTRAL, POSITIVE, VERY_POSITIVE)
        2. Główne emocje (ANGER, FEAR, HAPPINESS, SADNESS, SURPRISE, DISGUST, NEUTRAL) z wartościami od 0 do 1
        3. Pilność (LOW, NORMAL, HIGH, CRITICAL)
        4. Formalność (VERY_INFORMAL, INFORMAL, NEUTRAL, FORMAL, VERY_FORMAL)
        5. Główne tematy (lista słów kluczowych)
        6. Krótkie podsumowanie treści

        Odpowiedź podaj w formacie JSON.

        Wiadomość:
        {content}
        """

    async def _call_llm_api(self, prompt: str) -> str:
        """
        Wywołuje API modelu językowego.
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": 0.7,
                    "max_tokens": 1000,
                }

                async with session.post(f"{self.api_url}/api/generate", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("response", "")
                    else:
                        logger.error(f"Błąd API: {response.status}")
                        raise Exception(f"Błąd API LLM: {response.status}")
        except Exception as e:
            logger.error(f"Błąd podczas wywołania API LLM: {str(e)}")
            raise e

    def _parse_analysis_response(self, response: str) -> ToneAnalysis:
        """
        Parsuje odpowiedź API do modelu ToneAnalysis.
        """
        try:
            # Próba znalezienia bloku JSON w odpowiedzi
            import re

            json_match = re.search(r"{.*}", response, re.DOTALL)

            if not json_match:
                logger.warning("Nie znaleziono JSON w odpowiedzi LLM")
                return self._create_default_analysis()

            json_str = json_match.group(0)
            data = json.loads(json_str)

            # Przetwarzanie emocji
            emotions = {}
            if isinstance(data.get("emotions"), dict):
                for emotion_key, value in data["emotions"].items():
                    try:
                        emotion = Emotion(emotion_key)
                        emotions[emotion] = float(value)
                    except (ValueError, TypeError):
                        pass

            # Jeśli nie ma żadnych emocji, dodaj domyślną
            if not emotions:
                emotions[Emotion.NEUTRAL] = 1.0

            return ToneAnalysis(
                sentiment=self._parse_enum(data.get("sentiment"), Sentiment, Sentiment.NEUTRAL),
                emotions=emotions,
                urgency=self._parse_enum(data.get("urgency"), Urgency, Urgency.NORMAL),
                formality=self._parse_enum(data.get("formality"), Formality, Formality.NEUTRAL),
                top_topics=data.get("topTopics", []),
                summary_text=data.get("summaryText", ""),
            )

        except Exception as e:
            logger.error(f"Błąd podczas parsowania odpowiedzi API: {str(e)}")
            return self._create_default_analysis()

    def _parse_enum(self, value, enum_class, default):
        """
        Bezpiecznie parsuje wartość do enuma.
        """
        if value is None:
            return default

        try:
            return enum_class(value)
        except ValueError:
            return default

    async def generate_auto_reply(
        self, email_content: str, sender_name: str, email_history: list = None
    ) -> str:
        """
        Generuje automatyczną odpowiedź na wiadomość email przy użyciu MCP (Model Context Protocol).

        Args:
            email_content: Treść wiadomości email
            sender_name: Nazwa nadawcy
            email_history: Historia wcześniejszych wiadomości od tego nadawcy (opcjonalnie)

        Returns:
            Wygenerowana treść odpowiedzi
        """
        try:
            logger.info("Generowanie automatycznej odpowiedzi...")

            # Tworzenie kontekstu MCP
            mcp_context = self._create_mcp_context(email_content, sender_name, email_history)

            # Wywołanie API modelu z kontekstem MCP
            response = await self._call_llm_api_with_mcp(mcp_context)

            if not response or response.strip() == "":
                logger.warning("Otrzymano pustą odpowiedź z modelu LLM")
                return self._create_default_reply(sender_name)

            return response

        except Exception as e:
            logger.error(f"Błąd podczas generowania automatycznej odpowiedzi: {str(e)}")
            return self._create_default_reply(sender_name)

    def _create_mcp_context(
        self, email_content: str, sender_name: str, email_history: list = None
    ) -> dict:
        """
        Tworzy kontekst MCP (Model Context Protocol) dla modelu LLM.
        """
        # Podstawowe informacje o firmie
        company_info = {
            "name": "Fin Officer",
            "service": "Usługi finansowe i księgowe",
            "contact_email": "contact@fin-officer.com",
            "support_email": "support@fin-officer.com",
            "website": "https://fin-officer.com",
        }

        # Przygotowanie historii wiadomości
        conversation_history = []
        if email_history:
            for prev_email in email_history:
                conversation_history.append(
                    {
                        "role": "user" if prev_email.get("from_user", False) else "assistant",
                        "content": prev_email.get("content", ""),
                        "timestamp": prev_email.get("timestamp", ""),
                    }
                )

        # Tworzenie pełnego kontekstu MCP
        mcp_context = {
            "context": {
                "company": company_info,
                "current_date": datetime.now().strftime("%Y-%m-%d"),
                "sender": {"name": sender_name},
                "email": {"content": email_content},
                "conversation_history": conversation_history,
            },
            "instructions": [
                "Jesteś asystentem obsługi klienta firmy Fin Officer.",
                "Odpowiedz uprzejmie i profesjonalnie na wiadomość email.",
                "Twój ton powinien być pomocny, ale zwięzły.",
                "Nie wymyslaj informacji, których nie ma w kontekście.",
                "Jeśli nie znasz odpowiedzi, zaproponuj kontakt z zespołem wsparcia.",
                "Podpisz się jako 'Zespół Fin Officer'.",
                "Odpowiedź powinna mieć maksymalnie 5-7 zdań.",
            ],
            "output_format": "text",
        }

        return mcp_context

    async def _call_llm_api_with_mcp(self, mcp_context: dict) -> str:
        """
        Wywołuje API modelu językowego z kontekstem MCP.
        """
        try:
            # Konwersja kontekstu MCP na format JSON
            mcp_json = json.dumps(mcp_context, ensure_ascii=False)

            # Tworzenie promptu z kontekstem MCP
            prompt = f"""
            <mcp>
            {mcp_json}
            </mcp>
            
            Wygeneruj odpowiedź na powyższą wiadomość email zgodnie z instrukcjami MCP.
            """

            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "stream": False,
                }

                async with session.post(f"{self.api_url}/api/generate", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("response", "")
                    else:
                        logger.error(f"Błąd API: {response.status}")
                        raise Exception(f"Błąd API LLM: {response.status}")
        except Exception as e:
            logger.error(f"Błąd podczas wywołania API LLM z MCP: {str(e)}")
            raise e

    def _create_default_reply(self, sender_name: str) -> str:
        """
        Tworzy domyślną odpowiedź w przypadku błędu.
        """
        return f"""
Szanowny/a {sender_name},

Dziękujemy za wiadomość. Otrzymaliśmy Twoje zapytanie i postaramy się odpowiedzieć jak najszybciej.

W razie pilnej sprawy, prosimy o kontakt telefoniczny pod numerem +48 123 456 789.

Z poważaniem,
Zespół Fin Officer
"""

    def _create_default_analysis(self) -> ToneAnalysis:
        """
        Tworzy domyślną analizę tonu.
        """
        return ToneAnalysis(
            sentiment=Sentiment.NEUTRAL,
            emotions={Emotion.NEUTRAL: 0.8, Emotion.HAPPINESS: 0.1, Emotion.SURPRISE: 0.1},
            urgency=Urgency.NORMAL,
            formality=Formality.NEUTRAL,
            top_topics=["zapytanie", "informacja"],
            summary_text="Brak możliwości analizy wiadomości.",
        )
