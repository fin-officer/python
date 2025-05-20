#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TinyLLM Email Processing MCP Server

This module implements a Model Context Protocol (MCP) server for email processing
using TinyLLM. It provides tools for analyzing email content, generating auto-replies,
and storing emails in a SQL database with attachment information.
"""

import json
import logging
import os
import re
import hashlib
import base64
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP, Context, Image
from mcp.server.fastmcp.prompts import base

# Load environment variables
load_dotenv()

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)

# Create an MCP server for email processing
mcp_server_name = os.getenv('MCP_EMAIL_SERVER_NAME', 'Fin Officer TinyLLM Email Processor')
mcp_server_stateless = os.getenv('MCP_EMAIL_SERVER_STATELESS', 'false').lower() == 'true'

mcp = FastMCP(mcp_server_name, 
             dependencies=["fastapi", "pydantic", "aiohttp", "sqlite3"],
             stateless_http=mcp_server_stateless)


# Email processing configuration resource
@mcp.resource("email-config://settings")
def get_email_settings() -> Dict[str, Any]:
    """Get email processing settings"""
    return {
        "auto_reply": os.getenv('MCP_AUTO_REPLY_ENABLED', 'true').lower() == 'true',
        "save_to_database": os.getenv('MCP_SAVE_TO_DB', 'true').lower() == 'true',
        "database_path": os.getenv('DATABASE_URL', 'sqlite:///data/emails.db').replace('sqlite:///', ''),
        "company_name": os.getenv('MCP_COMPANY_NAME', 'Fin Officer'),
        "company_email": os.getenv('MCP_COMPANY_CONTACT_EMAIL', 'contact@finofficer.com'),
        "signature": os.getenv('MCP_EMAIL_SIGNATURE', 'Z powau017caniem,\nZespu00f3u0142 Fin Officer'),
        "max_history_emails": int(os.getenv('MCP_MAX_HISTORY_EMAILS', '5'))
    }


# Email templates resource
@mcp.resource("email-templates://{template_name}")
def get_email_template(template_name: str) -> str:
    """Get an email template by name"""
    # Get template directory from environment variable
    template_dir = os.getenv('TEMPLATE_DIR', '/data/templates')
    company_name = os.getenv('MCP_COMPANY_NAME', 'Fin Officer')
    
    # Default templates if file not found
    default_templates = {
        "welcome": f"Witamy w usu0142ugach {company_name}. Jesteu015bmy tutaj, aby pomu00f3c w zarzu0105dzaniu Twoimi finansami...",
        "support": f"Dziu0119kujemy za kontakt z naszym zespou0142em wsparcia. Analizujemy Twoje zgu0142oszenie...",
        "followup": f"W nawiu0105zaniu do naszej wczeu015bniejszej korespondencji, chcielibyu015bmy zapytau0107...",
        "auto_reply": f"Dziu0119kujemy za wiadomou015bu0107. Nasz zespu00f3u0142 zapozna siu0119 z niu0105 i odpowie najszybciej jak to mou017cliwe.\n\nZ powau017caniem,\nZespu00f3u0142 {company_name}"
    }
    
    # Try to load template from file
    template_path = os.path.join(template_dir, f"{template_name}.template")
    if os.path.exists(template_path):
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading template file {template_path}: {str(e)}")
    
    # Return default template if file not found
    return default_templates.get(template_name, "Szablon nie zostau0142 znaleziony")


# Helper function to ensure database tables exist
def _ensure_tables_exist(conn: sqlite3.Connection) -> None:
    """Create database tables if they don't exist"""
    cursor = conn.cursor()
    
    # Create emails table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emails (
        email_id TEXT PRIMARY KEY,
        sender_name TEXT,
        sender_email TEXT,
        recipient_email TEXT,
        subject TEXT,
        content TEXT,
        received_date TEXT,
        has_attachments BOOLEAN,
        analysis TEXT
    )
    """)
    
    # Create attachments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attachments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email_id TEXT,
        filename TEXT,
        storage_id TEXT,
        file_path TEXT,
        content_type TEXT,
        file_size INTEGER,
        analysis TEXT,
        FOREIGN KEY (email_id) REFERENCES emails (email_id)
    )
    """)
    
    # Create replies table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS replies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email_id TEXT,
        reply_content TEXT,
        sent_date TEXT,
        template_used TEXT,
        FOREIGN KEY (email_id) REFERENCES emails (email_id)
    )
    """)
    
    conn.commit()


# Helper function to get email history
async def _get_email_history(sender_email: str, settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get email history for a sender from the database"""
    try:
        # Connect to database
        db_path = settings["database_path"]
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get recent emails
        cursor.execute(
            "SELECT email_id, subject, content, received_date FROM emails "
            "WHERE sender_email = ? ORDER BY received_date DESC LIMIT ?",
            (sender_email, settings["max_history_emails"])
        )
        
        emails = []
        for row in cursor.fetchall():
            email_id, subject, content, received_date = row
            
            # Get replies for this email
            cursor.execute(
                "SELECT reply_content, sent_date FROM replies WHERE email_id = ?",
                (email_id,)
            )
            
            replies = []
            for reply_row in cursor.fetchall():
                reply_content, sent_date = reply_row
                replies.append({
                    "content": reply_content,
                    "sent_date": sent_date,
                    "from_user": False
                })
            
            # Add email to history
            emails.append({
                "email_id": email_id,
                "subject": subject,
                "content": content,
                "received_date": received_date,
                "from_user": True,
                "replies": replies
            })
        
        # Flatten the history into a chronological list
        history = []
        for email in emails:
            history.append({
                "content": f"Subject: {email['subject']}\n\n{email['content']}",
                "timestamp": email["received_date"],
                "from_user": True
            })
            
            for reply in email["replies"]:
                history.append({
                    "content": reply["content"],
                    "timestamp": reply["sent_date"],
                    "from_user": False
                })
        
        # Sort by timestamp
        history.sort(key=lambda x: x["timestamp"])
        
        return history
    
    except Exception as e:
        logger.error(f"Error getting email history: {str(e)}")
        return []
    
    finally:
        # Close database connection if it exists
        if 'conn' in locals():
            conn.close()


# Helper function to analyze email with TinyLLM
async def _analyze_with_tinyllm(email_content: str, subject: str, sender_name: str, sender_email: str) -> Dict[str, Any]:
    """Use TinyLLM to analyze email content"""
    try:
        import httpx
        
        # Get TinyLLM API URL and model from environment variables
        api_url = os.getenv("LLM_API_URL", "http://tinyllm:11434")
        model = os.getenv("LLM_MODEL", "llama2")
        
        # Create prompt for email analysis
        prompt = f"""
        You are an email analysis system for Fin Officer, a financial services company.
        Analyze the following email and provide a structured analysis.
        
        From: {sender_name} <{sender_email}>
        Subject: {subject}
        
        {email_content}
        
        Respond in JSON format with the following structure:
        {{
          "tone": "formal/informal/neutral",
          "urgency": "high/medium/low",
          "category": "support/inquiry/feedback/complaint/other",
          "sentiment": "positive/negative/neutral",
          "key_topics": ["list", "of", "key", "topics"],
          "entities": ["list", "of", "entities", "mentioned"],
          "requires_action": true/false,
          "summary": "Brief summary of the email content"
        }}
        """
        
        # Call TinyLLM API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "temperature": 0.2,
                    "max_tokens": 500,
                    "stream": False
                },
                timeout=15.0
            )
            
            if response.status_code == 200:
                result = response.json()
                llm_response = result.get("response", "")
                
                # Try to parse JSON response
                try:
                    # Find JSON in the response (it might be surrounded by other text)
                    json_match = re.search(r'\{[\s\S]*\}', llm_response)
                    if json_match:
                        json_str = json_match.group(0)
                        analysis = json.loads(json_str)
                        return analysis
                except json.JSONDecodeError:
                    # If JSON parsing fails, return a basic analysis
                    pass
            
            # Default response if API call fails or JSON parsing fails
            return {
                "tone": "neutral",
                "urgency": "medium",
                "category": "inquiry",
                "sentiment": "neutral",
                "key_topics": [],
                "entities": [],
                "requires_action": True,
                "summary": "Email content could not be analyzed"
            }
    
    except Exception as e:
        logger.error(f"Error in TinyLLM analysis: {str(e)}")
        return {
            "tone": "neutral",
            "urgency": "medium",
            "category": "inquiry",
            "sentiment": "neutral",
            "key_topics": [],
            "entities": [],
            "requires_action": True,
            "summary": f"Error in analysis: {str(e)}"
        }


# Helper function to extract entities from email content
async def _extract_entities(email_content: str) -> List[str]:
    """Extract named entities from email content"""
    try:
        import httpx
        
        # Get TinyLLM API URL and model from environment variables
        api_url = os.getenv("LLM_API_URL", "http://tinyllm:11434")
        model = os.getenv("LLM_MODEL", "llama2")
        
        # Create prompt for entity extraction
        prompt = f"""
        Extract all named entities from the following email content.
        Include people, organizations, locations, dates, monetary values, and account numbers.
        
        Email content:
        {email_content}
        
        Respond with a JSON array of entities, like: ["John Smith", "Acme Corp", "$500", "June 15, 2025"]
        """
        
        # Call TinyLLM API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "temperature": 0.2,
                    "max_tokens": 200,
                    "stream": False
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                llm_response = result.get("response", "")
                
                # Try to parse JSON response
                try:
                    # Find JSON array in the response
                    json_match = re.search(r'\[[^\]]*\]', llm_response)
                    if json_match:
                        json_str = json_match.group(0)
                        entities = json.loads(json_str)
                        return entities
                except json.JSONDecodeError:
                    # If JSON parsing fails, try to extract entities using regex
                    entities = re.findall(r'"([^"]+)"', llm_response)
                    if entities:
                        return entities
        
        # Default empty list if extraction fails
        return []
    
    except Exception as e:
        logger.error(f"Error extracting entities: {str(e)}")
        return []


# Helper function to generate reply with TinyLLM
async def _generate_reply_with_tinyllm(email_content: str, subject: str, sender_name: str, template: str, analysis: Dict[str, Any], email_history: List[Dict[str, Any]]) -> str:
    """Generate an email reply using TinyLLM"""
    try:
        import httpx
        
        # Get TinyLLM API URL and model from environment variables
        api_url = os.getenv("LLM_API_URL", "http://tinyllm:11434")
        model = os.getenv("LLM_MODEL", "llama2")
        
        # Format email history for context
        history_text = ""
        if email_history:
            history_text = "\n\nPrevious conversation history:\n"
            for i, msg in enumerate(email_history[-3:], 1):  # Include up to 3 most recent messages
                role = "Customer" if msg["from_user"] else "Fin Officer"
                history_text += f"{i}. {role}: {msg['content'][:200]}...\n"
        
        # Format analysis for context
        analysis_text = ""
        if analysis:
            analysis_text = "\n\nEmail analysis:\n"
            for key, value in analysis.items():
                if key in ["tone", "urgency", "category", "sentiment", "requires_action", "summary"]:
                    analysis_text += f"{key}: {value}\n"
        
        # Create prompt for reply generation
        prompt = f"""
        You are a customer service representative for Fin Officer, a financial services company.
        Generate a professional reply to the following email based on the provided template.
        
        From: {sender_name}
        Subject: {subject}
        
        Email content:
        {email_content}
        {analysis_text}
        {history_text}
        
        Template to use as a basis for your reply:
        {template}
        
        Your reply should be professional, helpful, and address the specific points raised in the email.
        Make sure to personalize the response based on the sender's name and inquiry.
        Sign the email with 'Z poważaniem,\nZespół Fin Officer'
        """
        
        # Call TinyLLM API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "temperature": 0.7,  # Higher temperature for more creative responses
                    "max_tokens": 1000,
                    "stream": False
                },
                timeout=20.0
            )
            
            if response.status_code == 200:
                result = response.json()
                reply = result.get("response", "")
                
                # Clean up the reply (remove any markdown formatting, etc.)
                reply = re.sub(r'^```[a-z]*\n', '', reply)  # Remove opening code block markers
                reply = re.sub(r'\n```$', '', reply)      # Remove closing code block markers
                
                return reply.strip()
        
        # Default reply if API call fails
        return f"Szanowny/a {sender_name},\n\nDziękujemy za wiadomość. Nasz zespół zapozna się z nią i odpowie najszybciej jak to możliwe.\n\nZ poważaniem,\nZespół Fin Officer"
    
    except Exception as e:
        logger.error(f"Error generating reply: {str(e)}")
        return f"Szanowny/a {sender_name},\n\nDziękujemy za wiadomość. Nasz zespół zapozna się z nią i odpowie najszybciej jak to możliwe.\n\nZ poważaniem,\nZespół Fin Officer"


# Email analysis tool
@mcp.tool()
async def analyze_email(email_content: str, 
                     subject: str,
                     sender_name: str,
                     sender_email: str,
                     has_attachments: bool = False,
                     ctx: Context = None) -> Dict[str, Any]:
    """Analyze an email for tone, urgency, and content classification"""
    try:
        # Use TinyLLM for email analysis
        analysis = await _analyze_with_tinyllm(email_content, subject, sender_name, sender_email)
        
        # Add metadata
        analysis["has_attachments"] = has_attachments
        analysis["length"] = len(email_content)
        analysis["word_count"] = len(email_content.split())
        
        # Extract key entities if not already present
        if "entities" not in analysis:
            analysis["entities"] = await _extract_entities(email_content)
        
        return analysis
    
    except Exception as e:
        logger.error(f"Error analyzing email: {str(e)}")
        # Return basic analysis on error
        return {
            "tone": "neutral",
            "urgency": "medium",
            "category": "general",
            "sentiment": "neutral",
            "error": str(e)
        }


# Email storage tool
@mcp.tool()
async def store_email(sender_name: str,
                   sender_email: str,
                   recipient_email: str,
                   subject: str,
                   content: str,
                   received_date: str = None,
                   attachments: List[Dict[str, Any]] = None,
                   analysis: Dict[str, Any] = None,
                   ctx: Context = None) -> Dict[str, Any]:
    """Store an email in the SQL database"""
    result = {
        "success": False,
        "email_id": None,
        "error": None
    }
    
    try:
        # Get email settings
        if ctx:
            settings, _ = await ctx.read_resource("email-config://settings")
        else:
            settings = get_email_settings()
        
        if not settings["save_to_database"]:
            result["success"] = True
            result["message"] = "Email storage is disabled"
            return result
        
        # Connect to database
        db_path = settings["database_path"]
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Ensure tables exist
        _ensure_tables_exist(conn)
        
        # Generate email ID
        email_hash = hashlib.md5(f"{sender_email}:{subject}:{content[:100]}".encode()).hexdigest()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        email_id = f"{timestamp}_{email_hash[:8]}"
        
        # Use provided date or current date
        if received_date:
            try:
                # Try to parse the provided date
                received_datetime = datetime.fromisoformat(received_date)
                received_timestamp = received_datetime.isoformat()
            except ValueError:
                received_timestamp = datetime.now().isoformat()
        else:
            received_timestamp = datetime.now().isoformat()
        
        # Convert analysis to JSON string if provided
        analysis_json = json.dumps(analysis) if analysis else None
        
        # Insert email into database
        cursor.execute(
            "INSERT INTO emails (email_id, sender_name, sender_email, recipient_email, subject, content, received_date, has_attachments, analysis) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (email_id, sender_name, sender_email, recipient_email, subject, content, received_timestamp, bool(attachments), analysis_json)
        )
        
        # Insert attachments if provided
        if attachments:
            for attachment in attachments:
                cursor.execute(
                    "INSERT INTO attachments (email_id, filename, storage_id, file_path, content_type, file_size, analysis) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (email_id, attachment.get("filename"), attachment.get("storage_id"), 
                     attachment.get("file_path"), attachment.get("content_type"), 
                     attachment.get("file_size"), json.dumps(attachment.get("analysis", {})))
                )
        
        # Commit changes
        conn.commit()
        
        # Update result
        result["success"] = True
        result["email_id"] = email_id
        
        return result
    
    except Exception as e:
        logger.error(f"Error storing email: {str(e)}")
        result["error"] = str(e)
        return result
    
    finally:
        # Close database connection if it exists
        if 'conn' in locals():
            conn.close()


# Email auto-reply generation tool
@mcp.tool()
async def generate_auto_reply(email_content: str, 
                           subject: str,
                           sender_name: str,
                           sender_email: str,
                           analysis: Dict[str, Any] = None,
                           ctx: Context = None) -> Dict[str, Any]:
    """Generate an auto-reply to an email based on its content and analysis"""
    result = {
        "reply_content": "",
        "should_send": True,
        "template_used": None
    }
    
    try:
        # Get email settings
        if ctx:
            settings, _ = await ctx.read_resource("email-config://settings")
        else:
            settings = get_email_settings()
        
        if not settings["auto_reply"]:
            result["should_send"] = False
            result["reply_content"] = "Auto-reply is disabled"
            return result
        
        # Get email history if available
        email_history = await _get_email_history(sender_email, settings)
        
        # Analyze email if analysis not provided
        if not analysis:
            analysis = await analyze_email(email_content, subject, sender_name, sender_email)
        
        # Determine appropriate template based on analysis
        template_name = "auto_reply"  # Default template
        
        if analysis.get("category") == "support":
            template_name = "support"
        elif analysis.get("category") == "welcome" or len(email_history) == 0:
            template_name = "welcome"
        elif analysis.get("category") == "followup":
            template_name = "followup"
        
        # Get template
        if ctx:
            template, _ = await ctx.read_resource(f"email-templates://{template_name}")
        else:
            template = get_email_template(template_name)
        
        # Generate personalized reply using TinyLLM
        reply_content = await _generate_reply_with_tinyllm(
            email_content, subject, sender_name, template, analysis, email_history
        )
        
        # Update result
        result["reply_content"] = reply_content
        result["template_used"] = template_name
        
        return result
    
    except Exception as e:
        logger.error(f"Error generating auto-reply: {str(e)}")
        # Return default reply on error
        company_name = settings["company_name"] if 'settings' in locals() else "Fin Officer"
        result["reply_content"] = f"Dziękujemy za wiadomość. Nasz zespół zapozna się z nią i odpowie najszybciej jak to możliwe.\n\nZ poważaniem,\nZespół {company_name}"
        result["error"] = str(e)
        return result


# Store reply tool
@mcp.tool()
async def store_reply(email_id: str,
                  reply_content: str,
                  template_used: str = None,
                  ctx: Context = None) -> Dict[str, Any]:
    """Store a reply in the database"""
    result = {
        "success": False,
        "error": None
    }
    
    try:
        # Get email settings
        if ctx:
            settings, _ = await ctx.read_resource("email-config://settings")
        else:
            settings = get_email_settings()
        
        if not settings["save_to_database"]:
            result["success"] = True
            result["message"] = "Reply storage is disabled"
            return result
        
        # Connect to database
        db_path = settings["database_path"]
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Ensure tables exist
        _ensure_tables_exist(conn)
        
        # Insert reply into database
        sent_date = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO replies (email_id, reply_content, sent_date, template_used) "
            "VALUES (?, ?, ?, ?)",
            (email_id, reply_content, sent_date, template_used)
        )
        
        # Commit changes
        conn.commit()
        
        # Update result
        result["success"] = True
        
        return result
    
    except Exception as e:
        logger.error(f"Error storing reply: {str(e)}")
        result["error"] = str(e)
        return result
    
    finally:
        # Close database connection if it exists
        if 'conn' in locals():
            conn.close()


# Email reply prompt
@mcp.prompt()
def email_reply_prompt(email_content: str, sender_name: str, template: str) -> List[base.Message]:
    """Create a prompt for generating an email reply"""
    return [
        base.SystemMessage("Jesteś asystentem obsługi klienta firmy Fin Officer, specjalizującej się w usługach finansowych i księgowych."),
        base.UserMessage(f"Otrzymałem następującą wiadomość email od {sender_name}:\n\n{email_content}\n\nProszę o przygotowanie odpowiedzi na podstawie tego szablonu:\n\n{template}"),
        base.AssistantMessage("Przygotowuję odpowiedź na tę wiadomość.")
    ]


# Run the server if executed directly
if __name__ == "__main__":
    # Get transport and mount path from environment variables
    transport = os.getenv('MCP_EMAIL_TRANSPORT', 'streamable-http')
    mount_path = os.getenv('MCP_EMAIL_MOUNT_PATH', '/mcp/email')
    
    # Run the server with configured settings
    mcp.run(transport=transport, mount_path=mount_path)
