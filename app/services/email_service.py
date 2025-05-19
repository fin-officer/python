import os
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aioimaplib
from dotenv import load_dotenv

from models import EmailSchema

# Załaduj zmienne środowiskowe
load_dotenv()

logger = logging.getLogger("email_service")


class EmailService:
    def __init__(self):
        # Konfiguracja SMTP
        self.smtp_host = os.getenv("EMAIL_HOST", "mailhog")
        self.smtp_port = int(os.getenv("EMAIL_PORT", 1025))
        self.smtp_user = os.getenv("EMAIL_USER", "test@example.com")
        self.smtp_password = os.getenv("EMAIL_PASSWORD", "")
        self.use_tls = os.getenv("EMAIL_USE_TLS", "False").lower() == "true"
        
        # Konfiguracja IMAP
        self.imap_host = os.getenv("IMAP_HOST", self.smtp_host)
        self.imap_port = int(os.getenv("IMAP_PORT", 993))
        self.imap_user = os.getenv("IMAP_USER", self.smtp_user)
        self.imap_password = os.getenv("IMAP_PASSWORD", self.smtp_password)
        
        logger.info(f"Inicjalizacja Email Service z SMTP: {self.smtp_host}:{self.smtp_port}, IMAP: {self.imap_host}:{self.imap_port}")
    
    async def send_email(self, to_email: str, subject: str, content: str, from_email: Optional[str] = None) -> bool:
        """
        Wysyła wiadomość email.
        """
        if not from_email:
            from_email = self.smtp_user
            
        try:
            logger.info(f"Wysyłanie wiadomości do {to_email} z tematem: {subject}")
            
            # Tworzenie wiadomości
            message = MIMEMultipart()
            message["From"] = from_email
            message["To"] = to_email
            message["Subject"] = subject
            message.attach(MIMEText(content, "plain"))
            
            # Wysyłanie wiadomości
            smtp = aiosmtplib.SMTP(hostname=self.smtp_host, port=self.smtp_port, use_tls=self.use_tls)
            await smtp.connect()
            
            if self.smtp_user and self.smtp_password:
                await smtp.login(self.smtp_user, self.smtp_password)
                
            await smtp.send_message(message)
            await smtp.quit()
            
            logger.info(f"Wiadomość wysłana pomyślnie do {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd podczas wysyłania wiadomości: {str(e)}")
            return False
    
    async def fetch_emails(self, max_emails: int = 10) -> List[EmailSchema]:
        """
        Pobiera wiadomości email z serwera IMAP.
        """
        try:
            logger.info("Pobieranie wiadomości email z serwera...")
            
            # Połączenie z serwerem IMAP
            imap_client = aioimaplib.IMAP4_SSL(host=self.imap_host, port=self.imap_port)
            await imap_client.wait_hello_from_server()
            
            # Logowanie
            if self.imap_user and self.imap_password:
                await imap_client.login(self.imap_user, self.imap_password)
            
            # Wybieranie skrzynki odbiorczej
            await imap_client.select("INBOX")
            
            # Wyszukiwanie nieprzeczytanych wiadomości
            _, data = await imap_client.search("UNSEEN")
            message_ids = data.decode().split()
            
            # Ograniczenie liczby wiadomości
            message_ids = message_ids[:max_emails]
            
            emails = []
            for msg_id in message_ids:
                _, data = await imap_client.fetch(msg_id, "(RFC822)")
                
                # Przetwarzanie wiadomości
                email = self._parse_email(data)
                if email:
                    emails.append(email)
                    
                # Oznaczanie wiadomości jako przeczytanej
                await imap_client.store(msg_id, "+FLAGS", "\\Seen")
            
            # Zamykanie połączenia
            await imap_client.logout()
            
            logger.info(f"Pobrano {len(emails)} wiadomości email")
            return emails
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania wiadomości: {str(e)}")
            return []
    
    def _parse_email(self, raw_data) -> Optional[EmailSchema]:
        """
        Parsuje surowe dane wiadomości email.
        """
        try:
            # Tutaj powinno być parsowanie wiadomości email
            # W uproszczonej wersji zwracamy testową wiadomość
            return EmailSchema(
                from_email="sender@example.com",
                to_email=self.smtp_user,
                subject="Testowa wiadomość",
                content="To jest treść testowej wiadomości email.",
                received_date=datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"Błąd podczas parsowania wiadomości: {str(e)}")
            return None
    
    async def check_connection(self) -> bool:
        """
        Sprawdza połączenie z serwerem email.
        """
        try:
            # Sprawdzanie połączenia SMTP
            smtp = aiosmtplib.SMTP(hostname=self.smtp_host, port=self.smtp_port, use_tls=self.use_tls)
            await smtp.connect()
            await smtp.quit()
            return True
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania połączenia z serwerem email: {str(e)}")
            return False