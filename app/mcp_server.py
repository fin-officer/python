#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MCP Server Implementation for Fin Officer

This module implements a Model Context Protocol (MCP) server for the Fin Officer application,
providing standardized access to resources, tools, and prompts for LLM interactions.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP, Context, Image
from mcp.server.fastmcp.prompts import base

# Load environment variables
load_dotenv()

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)

# Create an MCP server
mcp_server_name = os.getenv('MCP_SERVER_NAME', 'Fin Officer MCP')
mcp_server_stateless = os.getenv('MCP_SERVER_STATELESS', 'false').lower() == 'true'

mcp = FastMCP(mcp_server_name, 
             dependencies=["fastapi", "pydantic", "aiohttp", "aiosqlite"],
             stateless_http=mcp_server_stateless)  # Use environment variable for stateless setting


# Company information resource
@mcp.resource("company://info")
def get_company_info() -> Dict[str, str]:
    """Get company information as a resource"""
    return {
        "name": os.getenv('MCP_COMPANY_NAME', 'Fin Officer'),
        "service": os.getenv('MCP_COMPANY_SERVICE', 'Usługi finansowe i księgowe'),
        "contact_email": os.getenv('MCP_COMPANY_CONTACT_EMAIL', 'contact@finofficer.com'),
        "support_email": os.getenv('MCP_COMPANY_SUPPORT_EMAIL', 'support@finofficer.com'),
        "website": os.getenv('MCP_COMPANY_WEBSITE', 'https://finofficer.com'),
    }


# Email templates resource
@mcp.resource("templates://{template_name}")
def get_email_template(template_name: str) -> str:
    """Get an email template by name"""
    # Get template directory from environment variable
    template_dir = os.getenv('TEMPLATE_DIR', '/data/templates')
    company_name = os.getenv('MCP_COMPANY_NAME', 'Fin Officer')
    
    # Default templates if file not found
    default_templates = {
        "welcome": f"Witamy w usługach {company_name}. Jesteśmy tutaj, aby pomóc w zarządzaniu Twoimi finansami...",
        "support": f"Dziękujemy za kontakt z naszym zespołem wsparcia. Analizujemy Twoje zgłoszenie...",
        "followup": f"W nawiązaniu do naszej wcześniejszej korespondencji, chcielibyśmy zapytać..."
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
    return default_templates.get(template_name, "Szablon nie został znaleziony")


# Email analysis tool
@mcp.tool()
def analyze_email_tone(email_content: str) -> Dict[str, str]:
    """Analyze the tone and urgency of an email"""
    # This would typically call the LLM for analysis
    # Simplified implementation for demonstration
    analysis = {
        "tone": "professional",
        "urgency": "medium",
        "sentiment": "neutral",
        "key_topics": ["invoice", "payment", "deadline"],
    }
    logger.info(f"Analyzed email tone: {analysis}")
    return analysis


# Email reply generation tool
@mcp.tool()
async def generate_email_reply(email_content: str, 
                       sender_name: str, 
                       tone: str = "professional",
                       include_greeting: bool = True,
                       ctx: Context = None) -> str:
    """Generate a reply to an email with specified parameters"""
    # In a real implementation, this would use more sophisticated logic
    # or call another LLM service
    
    # Access company info from resource
    if ctx:
        try:
            company_data, _ = await ctx.read_resource("company://info")
            company_name = company_data.get("name", os.getenv('MCP_COMPANY_NAME', 'Fin Officer'))
        except Exception as e:
            logger.error(f"Error reading company resource: {str(e)}")
            company_name = os.getenv('MCP_COMPANY_NAME', 'Fin Officer')
    else:
        company_name = os.getenv('MCP_COMPANY_NAME', 'Fin Officer')
    
    # Generate reply based on tone
    greeting = f"Szanowny/a {sender_name},\n\n" if include_greeting else ""
    
    if tone == "formal":
        body = f"Dziękujemy za Pana/Pani wiadomość. Uprzejmie informujemy, że otrzymaliśmy zgłoszenie i zajmiemy się nim niezwłocznie."
    elif tone == "friendly":
        body = f"Dziękujemy za wiadomość! Z przyjemnością informujemy, że otrzymaliśmy Twoje zgłoszenie i wkrótce się nim zajmiemy."
    else:  # professional (default)
        body = f"Dziękujemy za kontakt z {company_name}. Potwierdzamy otrzymanie Pana/Pani wiadomości i zapewniamy, że zostanie ona rozpatrzona w najkrótszym możliwym terminie."
    
    signature = f"\n\nZ poważaniem,\nZespół {company_name}"
    
    reply = greeting + body + signature
    logger.info(f"Generated email reply with tone: {tone}")
    
    return reply


# Email history tool
@mcp.tool()
def get_email_history(email_address: str, max_entries: int = 5) -> List[Dict[str, Any]]:
    """Get email conversation history with a specific address"""
    # In a real implementation, this would query a database
    # Simplified mock data for demonstration
    history = [
        {
            "date": "2025-05-15T10:30:00",
            "direction": "incoming",
            "subject": "Zapytanie o fakturę",
            "content": "Dzień dobry, chciałbym zapytać o status mojej faktury nr FV/2025/04/123..."
        },
        {
            "date": "2025-05-15T14:45:00",
            "direction": "outgoing",
            "subject": "Re: Zapytanie o fakturę",
            "content": "Szanowny Kliencie, dziękujemy za kontakt. Faktura została opłacona dnia 10 maja..."
        },
        {
            "date": "2025-05-18T09:15:00",
            "direction": "incoming",
            "subject": "Podziękowanie",
            "content": "Dziękuję za szybką odpowiedź i wyjaśnienie sprawy..."
        }
    ]
    
    return history[:max_entries]


# Email reply prompt
@mcp.prompt()
def email_reply_prompt(email_content: str, sender_name: str) -> List[base.Message]:
    """Create a prompt for generating an email reply"""
    return [
        base.SystemMessage("Jesteś asystentem obsługi klienta firmy Fin Officer, specjalizującej się w usługach finansowych i księgowych."),
        base.UserMessage(f"Otrzymałem następującą wiadomość email od {sender_name}:\n\n{email_content}\n\nProszę o przygotowanie profesjonalnej odpowiedzi."),
        base.AssistantMessage("Przygotowuję odpowiedź na tę wiadomość. Czy masz jakieś szczególne wytyczne dotyczące tonu lub treści odpowiedzi?")
    ]


# Run the server if executed directly
if __name__ == "__main__":
    # Get transport and mount path from environment variables
    transport = os.getenv('MCP_TRANSPORT', 'streamable-http')
    mount_path = os.getenv('MCP_MOUNT_PATH', '/mcp')
    
    # Run the server with configured settings
    mcp.run(transport=transport, mount_path=mount_path)
