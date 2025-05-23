import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiosqlite
from dotenv import load_dotenv
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Załaduj zmienne środowiskowe
load_dotenv()

logger = logging.getLogger("db_service")

# Konfiguracja bazy danych
# Use a simple path in the current directory for testing
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/emails.db")

# Print debugging information
logger.info(f"Using database URL: {DATABASE_URL}")
db_path = DATABASE_URL.replace("sqlite:///", "").replace("sqlite+aiosqlite:///", "")
logger.info(f"Database file path: {db_path}")

# Convert SQLite URL to async version
if DATABASE_URL.startswith("sqlite:"):
    DATABASE_URL = DATABASE_URL.replace("sqlite:", "sqlite+aiosqlite:")

# Ensure parent directory exists
db_dir = os.path.dirname(db_path)
logger.info(f"Creating directory if needed: {db_dir}")
os.makedirs(db_dir, exist_ok=True)

# Check if directory is writable
if os.access(db_dir, os.W_OK):
    logger.info(f"Directory {db_dir} is writable")
else:
    logger.error(f"Directory {db_dir} is NOT writable")
    # Try to make it writable
    try:
        os.chmod(db_dir, 0o777)
        logger.info(f"Changed permissions on {db_dir}")
    except Exception as e:
        logger.error(f"Failed to change permissions: {str(e)}")

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
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


# Funkcja inicjalizująca bazę danych
async def init_db():
    try:
        async with engine.begin() as conn:
            # Use SQLAlchemy text() for raw SQL
            from sqlalchemy.sql import text

            create_table_sql = text(
                """
                CREATE TABLE IF NOT EXISTS emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_email TEXT NOT NULL,
                    to_email TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    content TEXT NOT NULL,
                    received_date TEXT NOT NULL,
                    status TEXT DEFAULT 'NEW',
                    tone_analysis TEXT,
                    sentiment TEXT,
                    replied BOOLEAN DEFAULT FALSE,
                    reply_date TEXT,
                    reply_content TEXT
                )
            """
            )
            await conn.execute(create_table_sql)
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
        query = (
            select(EmailTable)
            .where(EmailTable.from_email == from_email)
            .order_by(EmailTable.received_date.desc())
        )
        result = await session.execute(query)
        rows = result.scalars().all()

        history = []
        for row in rows:
            history.append(
                {
                    "id": row.id,
                    "subject": row.subject,
                    "date": row.received_date.isoformat() if row.received_date else "",
                    "sentiment": _extract_sentiment_from_analysis(row.tone_analysis),
                    "status": row.status,
                }
            )

        return history


# Funkcja zapisująca email do bazy danych
async def save_email(email_data: Dict[str, Any]) -> int:
    async with async_session() as session:
        # Konwersja string daty na obiekt datetime jeśli potrzebna
        if "received_date" in email_data and isinstance(email_data["received_date"], str):
            try:
                email_data["received_date"] = datetime.fromisoformat(email_data["received_date"])
            except ValueError:
                # Jeśli format daty jest niepoprawny, użyj aktualnej daty
                logger.warning(
                    f"Niepoprawny format daty: {email_data['received_date']}. Używam aktualnej daty."
                )
                email_data["received_date"] = datetime.now()

        new_email = EmailTable(**email_data)
        session.add(new_email)
        await session.commit()
        await session.refresh(new_email)
        return new_email.id


# Funkcja aktualizująca status emaila
async def update_email_status(
    email_id: int, status: str, tone_analysis: Optional[str] = None
) -> bool:
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
