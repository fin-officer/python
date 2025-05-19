import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from models import Sentiment, TemplateResponse, TemplateSchema, Urgency

# Załaduj zmienne środowiskowe
load_dotenv()

logger = logging.getLogger("template_service")


class TemplateService:
    def __init__(self):
        self.template_dir = Path(os.getenv("TEMPLATE_DIR", "/data/templates"))
        self.templates = {}
        logger.info(f"Inicjalizacja Template Service z katalogiem: {self.template_dir}")

    async def init_templates(self):
        """
        Inicjalizuje szablony, tworząc katalog i domyślne szablony jeśli nie istnieją
        """
        try:
            # Sprawdzenie czy katalog istnieje, jeśli nie to utworzenie go
            if not self.template_dir.exists():
                logger.info(f"Tworzenie katalogu szablonów: {self.template_dir}")
                self.template_dir.mkdir(parents=True, exist_ok=True)

            # Sprawdzenie czy są jakieś szablony w katalogu
            templates = list(self.template_dir.glob("*.template"))
            if not templates:
                logger.info("Brak szablonów, tworzenie domyślnych szablonów")
                await self._create_default_templates()

            # Załadowanie wszystkich szablonów
            await self._load_templates()

        except Exception as e:
            logger.error(f"Błąd podczas inicjalizacji szablonów: {str(e)}")
            # Upewnienie się, że mamy przynajmniej domyślny szablon
            self.templates["default"] = self._get_default_template()

    async def get_all_templates(self) -> List[TemplateSchema]:
        """
        Zwraca listę wszystkich dostępnych szablonów
        """
        if not self.templates:
            await self._load_templates()

        return [
            TemplateSchema(
                key=key,
                content=content,
                preview=content[:100] + "..." if len(content) > 100 else content,
            )
            for key, content in self.templates.items()
        ]

    async def get_template(self, template_key: str) -> Optional[TemplateResponse]:
        """
        Pobiera konkretny szablon na podstawie klucza
        """
        if not self.templates:
            await self._load_templates()

        content = self.templates.get(template_key)
        if content is None:
            return None

        return TemplateResponse(key=template_key, content=content)

    async def select_template_key(
        self, sentiment: Sentiment, urgency: Urgency, email_count: int = 0
    ) -> str:
        """
        Wybiera odpowiedni klucz szablonu na podstawie analizy i historii komunikacji
        """
        # Sprawdź, czy to pierwszy kontakt
        if email_count <= 1:
            return "default"

        # Sprawdź, czy to często kontaktujący się nadawca
        if email_count >= 5:
            return "frequent_sender" if "frequent_sender" in self.templates else "default"

        # Priorytetyzuj pilność
        if urgency in [Urgency.CRITICAL, Urgency.HIGH]:
            return "urgent_critical" if "urgent_critical" in self.templates else "default"

        # Następnie sprawdź sentyment
        if sentiment in [Sentiment.VERY_NEGATIVE, Sentiment.NEGATIVE]:
            return "negative_repeated" if "negative_repeated" in self.templates else "default"

        # Domyślny szablon
        return "default"

    async def fill_template(
        self,
        template_key: str,
        sender_name: str,
        subject: str,
        email_count: int = 0,
        last_email_date: str = "",
        sentiment: Optional[str] = None,
        urgency: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> str:
        """
        Wypełnia szablon danymi
        """
        if not self.templates:
            await self._load_templates()

        # Pobierz szablon lub użyj domyślnego, jeśli określony nie istnieje
        template = self.templates.get(
            template_key, self.templates.get("default", self._get_default_template())
        )

        # Podstawowe zmienne
        template = template.replace("{{SENDER_NAME}}", sender_name)
        template = template.replace("{{SUBJECT}}", subject)
        template = template.replace("{{CURRENT_DATE}}", self._get_current_date())

        # Opcjonalne zmienne
        if email_count > 0:
            template = template.replace("{{EMAIL_COUNT}}", str(email_count))

        if last_email_date:
            template = template.replace("{{LAST_EMAIL_DATE}}", last_email_date)

        if sentiment:
            template = template.replace("{{SENTIMENT}}", sentiment)

        if urgency:
            template = template.replace("{{URGENCY}}", urgency)

        if summary:
            template = template.replace("{{SUMMARY}}", summary)

        return template

    async def _load_templates(self):
        """
        Ładuje wszystkie szablony z katalogu
        """
        self.templates = {}
        try:
            for template_path in self.template_dir.glob("*.template"):
                try:
                    key = template_path.stem
                    content = template_path.read_text(encoding="utf-8")
                    self.templates[key] = content
                    logger.debug(f"Załadowano szablon: {key}")
                except Exception as e:
                    logger.error(f"Błąd podczas ładowania szablonu {template_path}: {str(e)}")

            logger.info(f"Załadowano {len(self.templates)} szablonów")

            # Upewnienie się, że mamy domyślny szablon
            if "default" not in self.templates:
                self.templates["default"] = self._get_default_template()

        except Exception as e:
            logger.error(f"Błąd podczas ładowania szablonów: {str(e)}")
            self.templates["default"] = self._get_default_template()

    async def _create_default_templates(self):
        """
        Tworzy domyślne szablony w katalogu szablonów
        """
        templates = {
            "default": self._get_default_template(),
            "frequent_sender": """
Szanowny/a {{SENDER_NAME}},

Dziękujemy za Twoją wiadomość dotyczącą: "{{SUBJECT}}".

Doceniamy Twoją lojalność i częsty kontakt z nami. Jako nasz stały klient, Twoja sprawa zostanie rozpatrzona priorytetowo.

To już Twoja {{EMAIL_COUNT}}. wiadomość do nas. Ostatnio kontaktowałeś/aś się z nami {{LAST_EMAIL_DATE}}.

Z poważaniem,
Zespół Obsługi Klienta
""",
            "negative_repeated": """
Szanowny/a {{SENDER_NAME}},

Dziękujemy za ponowną wiadomość dotyczącą: "{{SUBJECT}}".

Widzimy, że to nie pierwszy raz, gdy napotykasz problemy. Bardzo przepraszamy za tę sytuację. Twoja sprawa została przekazana do kierownika zespołu, który osobiście zajmie się jej rozwiązaniem.

Skontaktujemy się z Tobą najszybciej jak to możliwe.

Z poważaniem,
Zespół Obsługi Klienta
""",
            "urgent_critical": """
Szanowny/a {{SENDER_NAME}},

Dziękujemy za wiadomość dotyczącą: "{{SUBJECT}}".

Zauważyliśmy, że Twoja sprawa jest krytycznie pilna. Przekazaliśmy ją do natychmiastowego rozpatrzenia przez nasz zespół.

Skontaktujemy się z Tobą najszybciej jak to możliwe.

Z poważaniem,
Zespół Obsługi Klienta
""",
        }

        for key, content in templates.items():
            template_path = self.template_dir / f"{key}.template"
            template_path.write_text(content, encoding="utf-8")
            logger.info(f"Utworzono szablon: {key}")

    def _get_default_template(self) -> str:
        """
        Zwraca domyślny szablon
        """
        return """
Szanowny/a {{SENDER_NAME}},

Dziękujemy za wiadomość dotyczącą: "{{SUBJECT}}".

Otrzymaliśmy Twoją wiadomość i zajmiemy się nią wkrótce.

Z poważaniem,
Zespół Obsługi Klienta
"""

    def _get_current_date(self) -> str:
        """
        Zwraca bieżącą datę w formacie polskim
        """
        from datetime import datetime

        return datetime.now().strftime("%d.%m.%Y")

    def extract_name_from_email(self, email: str) -> str:
        """
        Ekstrakcja imienia z adresu email
        """
        try:
            # Usuń < > jeśli występują w adresie
            if "<" in email and ">" in email:
                # Format "Jan Kowalski <jan@example.com>"
                name_part = email.split("<")[0].strip()
                if name_part:
                    return name_part
                # Pobierz adres jeśli nie ma nazwy
                email = email.split("<")[1].split(">")[0]

            # Pobierz część przed @
            name_part = email.split("@")[0]

            # Usuń cyfry i znaki specjalne, zamień _ i . na spacje
            import re

            name_only = re.sub(r"[0-9_\.]", " ", name_part)
            name_only = " ".join([part.capitalize() for part in name_only.split() if part])

            return name_only if name_only else "Klient"
        except Exception:
            return "Klient"
