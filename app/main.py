from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi_utils.tasks import repeat_every
from dotenv import load_dotenv
import os
import logging
from datetime import datetime
import asyncio
from sqlalchemy import text, select

from models import EmailSchema, EmailResponse, TemplateListResponse, TemplateResponse
from services.email_service import EmailService
from services.llm_service import LlmService
from services.template_service import TemplateService
from services.db_service import get_db, init_db, EmailTable, get_email_history, save_email
from processors.email_processor import process_email, archive_email

# Załaduj zmienne środowiskowe
load_dotenv()

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Inicjalizacja usług
email_service = EmailService()
llm_service = LlmService()
template_service = TemplateService()

# Inicjalizacja aplikacji FastAPI
app = FastAPI(
    title="Email LLM Processor",
    description="Aplikacja do przetwarzania wiadomości email z wykorzystaniem LLM",
    version="1.0.0"
)

# Konfiguracja CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Zdarzenie startowe aplikacji
@app.on_event("startup")
async def startup_event():
    await init_db()
    logger.info("Aplikacja uruchomiona")


# Task w tle do pobierania wiadomości email
async def fetch_emails_task():
    try:
        emails = await email_service.fetch_emails()
        logger.info(f"Pobrano {len(emails)} wiadomości email")
        
        for email in emails:
            # Przetwarzanie emaila w tle
            await process_email(email)
            
    except Exception as e:
        logger.error(f"Błąd podczas pobierania wiadomości email: {str(e)}")


# Endpoint do ręcznego przetwarzania wiadomości
@app.post("/api/emails/process", response_model=EmailResponse)
async def process_email_endpoint(
        email: EmailSchema,
        background_tasks: BackgroundTasks,
        db=Depends(get_db)
):
    try:
        # Zapisanie emaila do bazy danych
        email_id = await save_email({
            "from_email": email.from_email,
            "to_email": email.to_email,
            "subject": email.subject,
            "content": email.content,
            "received_date": email.received_date
        })
        
        # Przetwarzanie emaila w tle
        background_tasks.add_task(
            process_email,
            email
        )
        
        return {"id": email_id, "status": "PROCESSING", "message": "Wiadomość przyjęta do przetworzenia"}
    except Exception as e:
        logger.error(f"Błąd podczas przetwarzania wiadomości: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint do pobierania listy szablonów
@app.get("/api/templates", response_model=TemplateListResponse)
async def get_templates():
    try:
        templates = await template_service.get_all_templates()
        return {"templates": templates}
    except Exception as e:
        logger.error(f"Błąd podczas pobierania szablonów: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint do pobierania konkretnego szablonu
@app.get("/api/templates/{template_key}", response_model=TemplateResponse)
async def get_template(template_key: str):
    try:
        template = await template_service.get_template(template_key)
        if not template:
            raise HTTPException(status_code=404, detail=f"Szablon {template_key} nie istnieje")
        return {"template": template}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Błąd podczas pobierania szablonu: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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


# Endpoint do wysłania testowej wiadomości email
@app.post("/api/emails/send-test")
async def send_test_email(to_email: str = Query(..., description="Adres email odbiorcy")):
    try:
        content = "To jest testowa wiadomość wygenerowana przez Email LLM Processor."
        subject = "Test Email LLM Processor"
        result = await email_service.send_email(to_email, subject, content)
        
        if result:
            return {"status": "success", "message": f"Testowa wiadomość wysłana do {to_email}"}
        else:
            raise HTTPException(status_code=500, detail="Błąd podczas wysyłania wiadomości")
    except Exception as e:
        logger.error(f"Błąd podczas wysyłania testowej wiadomości: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint do ręcznego pobierania wiadomości email
@app.post("/api/emails/fetch")
async def fetch_emails_endpoint(background_tasks: BackgroundTasks):
    try:
        # Pobieranie emaili w tle
        background_tasks.add_task(
            fetch_emails_task
        )
        
        return {"status": "success", "message": "Rozpoczęto pobieranie wiadomości email"}
    except Exception as e:
        logger.error(f"Błąd podczas pobierania wiadomości: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint do automatycznego odpowiadania na wiadomości email z użyciem MCP
@app.post("/api/emails/{email_id}/auto-reply")
async def auto_reply_to_email_endpoint(
        email_id: int,
        background_tasks: BackgroundTasks = None,
        db=Depends(get_db)
):
    try:
        # Pobranie wiadomości z bazy danych używając SQLAlchemy ORM
        query = select(EmailTable).where(EmailTable.id == email_id)
        result = await db.execute(query)
        email_record = result.scalars().first()
        
        if not email_record:
            raise HTTPException(status_code=404, detail="Wiadomość nie znaleziona")
            
        # Konwersja rekordu na obiekt EmailSchema
        original_email = EmailSchema(
            id=email_record.id,
            from_email=email_record.from_email,
            to_email=email_record.to_email,
            subject=email_record.subject,
            content=email_record.content,
            received_date=str(email_record.received_date) if email_record.received_date else None
        )
        
        # Pobranie historii wiadomości od tego nadawcy
        email_history = await get_email_history(original_email.from_email)
        
        # Przygotowanie historii wiadomości w formacie dla MCP
        mcp_email_history = []
        for email in email_history:
            mcp_email_history.append({
                "from_user": True,  # Wiadomości od użytkownika
                "content": email.get("content", ""),
                "timestamp": email.get("received_date", "")
            })
            if email.get("reply_content"):
                mcp_email_history.append({
                    "from_user": False,  # Nasze odpowiedzi
                    "content": email.get("reply_content", ""),
                    "timestamp": email.get("reply_date", "")
                })
        
        # Ekstrakcja nazwy nadawcy z adresu email
        sender_name = original_email.from_email.split("@")[0]
        
        # Generowanie automatycznej odpowiedzi
        auto_reply_content = await llm_service.generate_auto_reply(
            email_content=original_email.content,
            sender_name=sender_name,
            email_history=mcp_email_history
        )
        
        # Wysyłanie odpowiedzi w tle jeśli podano background_tasks
        if background_tasks:
            background_tasks.add_task(
                email_service.reply_to_email,
                original_email,
                original_email.subject,
                auto_reply_content
            )
            return {"status": "success", "message": f"Automatyczna odpowiedź do {original_email.from_email} zostanie wysłana w tle", "content": auto_reply_content}
        
        # Wysyłanie odpowiedzi synchronicznie
        result = await email_service.reply_to_email(original_email, original_email.subject, auto_reply_content)
        
        if result:
            # Aktualizacja statusu wiadomości w bazie danych
            update_stmt = text(
                "UPDATE emails SET replied = TRUE, reply_date = :reply_date, reply_content = :reply_content WHERE id = :id"
            )
            await db.execute(
                update_stmt,
                {
                    "id": email_id,
                    "reply_date": datetime.now().isoformat(),
                    "reply_content": auto_reply_content
                }
            )
            
            return {"status": "success", "message": f"Automatyczna odpowiedź wysłana do {original_email.from_email}", "content": auto_reply_content}
        else:
            raise HTTPException(status_code=500, detail="Błąd podczas wysyłania automatycznej odpowiedzi")
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Błąd podczas automatycznego odpowiadania na wiadomość: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint do odpowiadania na wiadomości email
@app.post("/api/emails/{email_id}/reply")
async def reply_to_email_endpoint(
        email_id: int,
        content: str = Query(..., description="Treść odpowiedzi"),
        background_tasks: BackgroundTasks = None,
        db=Depends(get_db)
):
    try:
        # Pobranie wiadomości z bazy danych używając SQLAlchemy ORM
        query = select(EmailTable).where(EmailTable.id == email_id)
        result = await db.execute(query)
        email_record = result.scalars().first()
        
        if not email_record:
            raise HTTPException(status_code=404, detail="Wiadomość nie znaleziona")
            
        # Konwersja rekordu na obiekt EmailSchema
        original_email = EmailSchema(
            id=email_record.id,
            from_email=email_record.from_email,
            to_email=email_record.to_email,
            subject=email_record.subject,
            content=email_record.content,
            received_date=str(email_record.received_date) if email_record.received_date else None
        )
        
        # Wysyłanie odpowiedzi w tle jeśli podano background_tasks
        if background_tasks:
            background_tasks.add_task(
                email_service.reply_to_email,
                original_email,
                original_email.subject,
                content
            )
            return {"status": "success", "message": f"Odpowiedź do {original_email.from_email} zostanie wysłana w tle"}
        
        # Wysyłanie odpowiedzi synchronicznie
        result = await email_service.reply_to_email(original_email, original_email.subject, content)
        
        if result:
            # Aktualizacja statusu wiadomości w bazie danych
            update_stmt = text(
                "UPDATE emails SET replied = TRUE, reply_date = :reply_date, reply_content = :reply_content WHERE id = :id"
            )
            await db.execute(
                update_stmt,
                {
                    "id": email_id,
                    "reply_date": datetime.now().isoformat(),
                    "reply_content": content
                }
            )
            
            return {"status": "success", "message": f"Odpowiedź wysłana do {original_email.from_email}"}
        else:
            raise HTTPException(status_code=500, detail="Błąd podczas wysyłania odpowiedzi")
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Błąd podczas odpowiadania na wiadomość: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
