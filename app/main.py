from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi_utils.tasks import repeat_every
from dotenv import load_dotenv
import os
import logging
from datetime import datetime
import asyncio

from models import EmailSchema, EmailResponse, TemplateListResponse, TemplateResponse
from services.email_service import EmailService
from services.llm_service import LlmService
from services.template_service import TemplateService
from services.db_service import get_db, init_db
from processors.email_processor import process_email, archive_email

# Załaduj zmienne środowiskowe
load_dotenv()

# Konfiguracja loggera
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("email_processor")

# Inicjalizacja aplikacji FastAPI
app = FastAPI(
    title=os.getenv("APP_NAME", "Email LLM Processor"),
    description="API do przetwarzania wiadomości email z wykorzystaniem modeli językowych (LLM)",
    version="1.0.0",
)

# Dodanie middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicjalizacja usług
email_service = EmailService()
llm_service = LlmService()
template_service = TemplateService()


# Inicjalizacja bazy danych przy starcie
@app.on_event("startup")
async def startup_event():
    await init_db()
    await template_service.init_templates()
    logger.info("Aplikacja uruchomiona pomyślnie")


# Task w tle do pobierania wiadomości email
@app.on_event("startup")
@repeat_every(seconds=int(os.getenv("CHECK_EMAILS_INTERVAL", 60)))
async def fetch_emails_task():
    try:
        logger.info("Rozpoczęcie sprawdzania nowych wiadomości email")
        emails = await email_service.fetch_emails()
        for email in emails:
            await process_email(email, email_service, llm_service, template_service)
        logger.info(f"Zakończono sprawdzanie wiadomości. Przetworzono: {len(emails)}")
    except Exception as e:
        logger.error(f"Błąd podczas automatycznego sprawdzania wiadomości: {str(e)}")


# Endpoint do ręcznego przetwarzania wiadomości
@app.post("/api/emails/process", response_model=EmailResponse)
async def process_email_endpoint(
        email: EmailSchema,
        background_tasks: BackgroundTasks,
        db=Depends(get_db)
):
    try:
        # Przetwarzanie email w tle
        background_tasks.add_task(
            process_email,
            email,
            email_service,
            llm_service,
            template_service,
            db
        )

        return EmailResponse(
            id=0,  # ID będzie nadane podczas przetwarzania
            status="PROCESSING",
            message="Wiadomość przyjęta do przetworzenia"
        )
    except Exception as e:
        logger.error(f"Błąd podczas przetwarzania wiadomości: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint do pobierania listy szablonów
@app.get("/api/templates", response_model=TemplateListResponse)
async def get_templates():
    templates = await template_service.get_all_templates()
    return TemplateListResponse(templates=templates)


# Endpoint do pobierania konkretnego szablonu
@app.get("/api/templates/{template_key}", response_model=TemplateResponse)
async def get_template(template_key: str):
    template = await template_service.get_template(template_key)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Szablon '{template_key}' nie został znaleziony")
    return template


# Endpoint zdrowia aplikacji
@app.get("/health")
async def health_check():
    services_status = {
        "email_service": "UP" if await email_service.check_connection() else "DOWN",
        "llm_service": "UP" if await llm_service.check_connection() else "DOWN",
        "template_service": "UP" if len(await template_service.get_all_templates()) > 0 else "DOWN",
    }

    all_up = all(status == "UP" for status in services_status.values())

    return {
        "status": "UP" if all_up else "DEGRADED",
        "timestamp": datetime.now().isoformat(),
        "services": services_status
    }


# Endpoint do wysyłania testowej wiadomości email
@app.post("/api/emails/send-test")
async def send_test_email(to_email: str = Query(..., description="Adres email odbiorcy")):
    try:
        await email_service.send_email(
            to_email=to_email,
            subject="Test Email LLM Processor",
            content="To jest testowa wiadomość z Email LLM Processor."
        )
        return {"status": "success", "message": f"Testowa wiadomość wysłana do {to_email}"}
    except Exception as e:
        logger.error(f"Błąd podczas wysyłania testowej wiadomości: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)