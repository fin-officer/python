#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MCP Integration Example for Fin Officer

This module demonstrates how to integrate the MCP server with the FastAPI application
and use it for email processing and auto-reply generation.
"""

import logging
import os
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Import the MCP server
from mcp_server import mcp

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)

# Create FastAPI app
app_name = os.getenv('APP_NAME', 'Fin Officer MCP Integration')
app = FastAPI(title=app_name)

# Mount the MCP server to the FastAPI application
mount_path = os.getenv('MCP_MOUNT_PATH', '/mcp')
app.mount(mount_path, mcp.streamable_http_app(mount_path))


# Define data models
class EmailContent(BaseModel):
    sender: str
    sender_email: str
    subject: str
    content: str
    attachment_ids: List[str] = []


class EmailReply(BaseModel):
    status: str
    reply: str
    tone_analysis: Optional[Dict[str, Any]] = None


# Email processing endpoint using MCP
@app.post("/api/emails/process-mcp", response_model=EmailReply)
async def process_email_mcp(email: EmailContent, background_tasks: BackgroundTasks):
    """Process an email using MCP tools and resources"""
    try:
        # Use MCP to analyze email tone
        tone_analysis = await mcp.call_tool(
            "analyze_email_tone",
            {"email_content": email.content}
        )
        
        # Get email history if available
        try:
            email_history = await mcp.call_tool(
                "get_email_history",
                {"email_address": email.sender_email, "max_entries": 3}
            )
        except Exception as e:
            logger.warning(f"Could not retrieve email history: {str(e)}")
            email_history = []
        
        # Generate reply based on tone analysis
        reply = await mcp.call_tool(
            "generate_email_reply",
            {
                "email_content": email.content,
                "sender_name": email.sender,
                "tone": tone_analysis.get("tone", "professional"),
                "include_greeting": True
            }
        )
        
        # Schedule sending the reply in the background
        background_tasks.add_task(send_email_reply, email.sender_email, reply, email.subject)
        
        return EmailReply(
            status="success",
            reply=reply,
            tone_analysis=tone_analysis
        )
        
    except Exception as e:
        logger.error(f"Error processing email with MCP: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing email: {str(e)}")


# Get email reply prompt endpoint
@app.get("/api/prompts/email-reply")
async def get_email_reply_prompt(email_content: str, sender_name: str):
    """Get a prompt for generating an email reply"""
    try:
        prompt = await mcp.get_prompt(
            "email_reply_prompt",
            {"email_content": email_content, "sender_name": sender_name}
        )
        return {"prompt": prompt}
    except Exception as e:
        logger.error(f"Error getting email reply prompt: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting prompt: {str(e)}")


# List available MCP resources
@app.get("/api/mcp/resources")
async def list_mcp_resources():
    """List all available MCP resources"""
    try:
        resources = await mcp.list_resources()
        return {"resources": resources}
    except Exception as e:
        logger.error(f"Error listing MCP resources: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing resources: {str(e)}")


# List available MCP tools
@app.get("/api/mcp/tools")
async def list_mcp_tools():
    """List all available MCP tools"""
    try:
        tools = await mcp.list_tools()
        return {"tools": tools}
    except Exception as e:
        logger.error(f"Error listing MCP tools: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing tools: {str(e)}")


# Mock function for sending email replies
async def send_email_reply(recipient: str, content: str, subject: str):
    """Send an email reply (mock implementation)"""
    logger.info(f"Sending email to {recipient}")
    logger.info(f"Subject: Re: {subject}")
    logger.info(f"Content: {content}")
    # In a real implementation, this would use an email service
    return True


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "mcp_server": "running"}


# Run the application if executed directly
if __name__ == "__main__":
    import uvicorn
    # Get host and port from environment variables or use defaults
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '8000'))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    # Run the application
    uvicorn.run(app, host=host, port=port, debug=debug)
