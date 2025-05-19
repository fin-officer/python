import os
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

from models import EmailSchema, EmailStatus, Sentiment, Urgency, ToneAnalysis
from services.email_service import EmailService
from services.llm_service import LlmService
from services.template_service import TemplateService
from services.db_service import save_email, update_email_status, get_email_history

# Załaduj zmienne środowiskowe
load_dotenv()

logger = logging.getLogger("email_processor")


async def process_email(
        email: EmailSchema,
        email_service: EmailService,
        llm_service: LlmService,
        template_service: TemplateService,
        db=None
) -> int:
    """
    Główna funkcja przetwarzająca wiadomość email
    """
    try:
        logger.info(f"Rozpoczęcie przetwarzania wiadomości od: {email.from_email}")

        # Zapisanie email do bazy danych
        email_dict = {
            "from_email": email.from_email,
            "to_email": email.to_email,
            "subject": email.subject,
            "content": email.content,
            "received_date": datetime.now(),
            "status": EmailStatus.RECEIVED.value
        }

        email_id = await save_email(email_dict)
        logger.info(f"Email zapisany w bazie danych z ID: {email_id}")

        # Aktualizacja statusu
        await update_email_status(email_id, EmailStatus.PROCESSING.value)

        # Analiza tonu wiadomości
        tone_analysis = await llm_service.analyze_tone(email.content)
        logger.info(f"Analiza tonu zakończona: {tone_analysis.sentiment}, {tone_analysis.urgency}")

        # Zapisanie wyników analizy
        analysis_json = json.dumps({
            "sentiment": tone_analysis.sentiment.value,
            "emotions": {k.value: v for k, v in tone_analysis.emotions.items()},
            "urgency": tone_analysis.urgency.value,
            "formality": tone_analysis.formality.value,
            "top_topics": tone_analysis.top_topics,
            "summary_text": tone_analysis.summary_text
        })

        await update_email_status(email_id, EmailStatus.PROCESSED.value, analysis_json)

        # Archiwizacja wiadomości
        await archive_email(email, tone_analysis)

        # Sprawdzenie czy należy wysłać automatyczną odpowiedź
        if should_auto_reply(tone_analysis):
            logger.info(f"Generowanie odpowiedzi automatycznej dla wiadomości ID: {email_id}")

            # Pobranie historii komunikacji z nadawcą
            email_history = await get_email_history(email.from_email)

            # Wybór odpowiedniego szablonu
            template_key = await template_service.select_template_key(
                tone_analysis.sentiment,
                tone_analysis.urgency,
                len(email_history)
            )

            # Ekstrakcja imienia z adresu email
            sender_name = template_service.extract_name_from_email(email.from_email)

            # Dane o ostatniej wiadomości
            last_email_date = ""
            if len(email_history) > 1:
                try:
                    date_str = email_history[1]["date"]
                    last_email_date = datetime.fromisoformat(date_str).strftime("%d.%m.%Y")
                except Exception:
                    last_email_date = "wcześniej"

            # Wypełnienie szablonu
            reply_content = await template_service.fill_template(
                template_key=template_key,
                sender_name=sender_name,
                subject=email.subject or "",
                email_count=len(email_history),
                last_email_date=last_email_date,
                sentiment=translate_sentiment(tone_analysis.sentiment),
                urgency=translate_urgency(tone_analysis.urgency),
                summary=tone_analysis.summary_text
            )

            # Wysłanie odpowiedzi
            reply_subject = f"Re: {email.subject}" if email.subject else "Odpowiedź na Twoją wiadomość"
            sent = await email_service.send_email(
                to_email=email.from_email,
                subject=reply_subject,
                content=reply_content
            )

            if sent:
                await update_email_status(email_id, EmailStatus.REPLIED.value)
                logger.info(f"Wysłano automatyczną odpowiedź dla wiadomości ID: {email_id}")
            else:
                logger.error(f"Nie udało się wysłać automatycznej odpowiedzi dla wiadomości ID: {email_id}")

        return email_id

    except Exception as e:
        logger.error(f"Błąd podczas przetwarzania wiadomości: {str(e)}")
        if email_id:
            await update_email_status(email_id, EmailStatus.ERROR.value)
        raise e


def should_auto_reply(analysis: ToneAnalysis) -> bool:
    """
    Decyduje, czy należy wysłać automatyczną odpowiedź na podstawie analizy
    """
    # Przykładowa logika decyzji o automatycznej odpowiedzi
    return (
            analysis.urgency in [Urgency.HIGH, Urgency.CRITICAL] or
            analysis.sentiment in [Sentiment.NEGATIVE, Sentiment.VERY_NEGATIVE]
    )


async def archive_email(email: EmailSchema, analysis: Optional[ToneAnalysis] = None) -> bool:
    """
    Archiwizuje wiadomość email do pliku tekstowego
    """
    try:
        archive_dir = Path(os.getenv("ARCHIVE_DIR", "/data/archive"))

        # Sprawdzenie czy katalog istnieje, jeśli nie to utworzenie go
        if not archive_dir.exists():
            archive_dir.mkdir(parents=True, exist_ok=True)

        # Przygotowanie nazwy pliku: timestamp_od_email.txt
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_email = email.from_email.replace("@", "_at_").replace("<", "").replace(">", "")
        safe_email = "".join(c if c.isalnum() or c == "_" else "_" for c in safe_email)
        file_name = f"{timestamp}_{safe_email}.txt"

        # Przygotowanie zawartości archiwum
        content = []
        content.append(f"From: {email.from_email}")
        content.append(f"To: {email.to_email}")
        content.append(f"Subject: {email.subject or ''}")
        content.append(f"Received: {datetime.now().isoformat()}")
        content.append(f"Status: {EmailStatus.RECEIVED.value}")

        if analysis:
            content.append(f"Sentiment: {analysis.sentiment.value}")
            content.append(f"Urgency: {analysis.urgency.value}")

        content.append("")  # Pusta linia oddzielająca nagłówki od treści
        content.append(email.content)

        # Zapisanie pliku
        archive_path = archive_dir / file_name
        archive_path.write_text("\n".join(content), encoding="utf-8")

        logger.info(f"Wiadomość zarchiwizowana: {archive_path}")
        return True

    except Exception as e:
        logger.error(f"Błąd podczas archiwizacji wiadomości: {str(e)}")
        return False


def translate_sentiment(sentiment: Sentiment) -> str:
    """
    Tłumaczy sentyment na język polski
    """
    translations = {
        Sentiment.VERY_NEGATIVE: "bardzo negatywna",
        Sentiment.NEGATIVE: "negatywna",
        Sentiment.NEUTRAL: "neutralna",
        Sentiment.POSITIVE: "pozytywna",
        Sentiment.VERY_POSITIVE: "bardzo pozytywna"
    }
    return translations.get(sentiment, "neutralna")


def translate_urgency(urgency: Urgency) -> str:
    """
    Tłumaczy pilność na język polski
    """
    translations = {
        Urgency.CRITICAL: "krytyczna",
        Urgency.HIGH: "wysoka",
        Urgency.NORMAL: "normalna",
        Urgency.LOW: "niska"
    }
    return translations.get(urgency, "normalna")