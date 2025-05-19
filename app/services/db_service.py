import os
import logging
import aiosqlite
import json
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, Text, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from datetime import datetime
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

# Załaduj zmienne środowiskowe
load_dotenv()

logger = logging.getLogger("db_service")

# Konfiguracja bazy danych
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/emails.db")
if DATABASE_URL.startswith("sqlite:"):
    DATABASE_URL = DATABASE_URL.replace("sqlite:", "sqlite+aiosqlite:")

# Definicja modelu bazowego
Base = declarative_base()

# Definicja modelu Email
class EmailTable(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True)
    from_email = Column(String(255), nullable=False)
    to_email = Column(String(255), nullable=False)
    subject = Column(String(255))
    content = Column(Text)
    received_date = Column(DateTime, default=datetime.now)
    processed_date = Column(DateTime)
    tone_analysis = Column(Text)
    status = Column(String(50))

# Inicjalizacja silnika bazy danych
engine = create_async_engine(DATABASE_URL, echo=False)

# Sesja asynchroniczna
async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

# Funkcja inicjalizująca bazę danych
async def init_db():
    try:
        # Tworzenie tabel jeśli nie istnieją
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Baza danych zainicjalizowana pomyślnie")
    except Exception as e:
        logger.error(f"Błąd podczas inicjalizacji bazy danych: {str(e)}")
        raise e

# Funkcja zwracająca sesję bazy danych
async def get_db():
    async with async_session() as session:
        yield session

# Funkcja pobierająca historię emaili od danego nadawcy
async def get_email_history(from_email: str) -> List[Dict[str, Any]]:
    async with async_session() as session:
        query = select(EmailTable).where(EmailTable.from_email == from_email).order_by(EmailTable.received_date.desc())
        result = await session.execute(query)
        rows = result.scalars().all()

        history = []
        for row in rows:
            history.append({
                "id": row.id,
                "subject": row.subject,
                "date": row.received_date.isoformat() if row.received_date else "",
                "sentiment": _extract_sentiment_from_analysis(row.tone_analysis),
                "status": row.status
            })

        return history

# Funkcja zapisująca email do bazy danych
async def save_email(email_data: Dict[str, Any]) -> int:
    async with async_session() as session:
        new_email = EmailTable(**email_data)
        session.add(new_email)
        await session.commit()
        await session.refresh(new_email)
        return new_email.id

# Funkcja aktualizująca status emaila
async def update_email_status(email_id: int, status: str, tone_analysis: Optional[str] = None) -> bool:
    async with async_session() as session:
        query = select(EmailTable).where(EmailTable.id == email_id)
        result = await session.execute(query)
        email = result.scalars().first()

        if not email:
            return False

        email.status = status
        if tone_analysis:
            email.tone_analysis = tone_analysis
        email.processed_date = datetime.now()

        await session.commit()
        return True

# Funkcja pomocnicza do ekstrakcji sentymentu z JSON analizy tonu
def _extract_sentiment_from_analysis(analysis_json: Optional[str]) -> str:
    if not analysis_json:
        return "NEUTRAL"

    try:
        analysis = json.loads(analysis_json)
        return analysis.get("sentiment", "NEUTRAL")
    except Exception:
        return "NEUTRAL"