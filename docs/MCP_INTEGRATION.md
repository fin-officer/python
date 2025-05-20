# Model Context Protocol (MCP) Integration Guide

## Overview

The Model Context Protocol (MCP) allows applications to provide context for LLMs in a standardized way, separating the concerns of providing context from the actual LLM interaction. This document explains how MCP is implemented in the Fin Officer application and how to use it effectively.

## What is MCP?

The Model Context Protocol (MCP) lets you build servers that expose data and functionality to LLM applications in a secure, standardized way. Think of it like a web API, but specifically designed for LLM interactions. MCP servers can:

- Expose data through Resources (think of these sort of like GET endpoints; they are used to load information into the LLM's context)
- Provide functionality through Tools (sort of like POST endpoints; they are used to execute code or otherwise produce a side effect)
- Define interaction patterns through Prompts (reusable templates for LLM interactions)

## Current Implementation

Our application currently uses a simplified version of MCP to structure context for the TinyLLM Ollama model. The implementation includes:

1. **Context Creation**: The `_create_mcp_context` method in `LlmService` creates a structured context object with company information, email content, and conversation history.
2. **API Integration**: The `_call_llm_api_with_mcp` method sends the MCP context to the LLM API using a standardized format.
3. **Auto-Reply Functionality**: The `/api/emails/{email_id}/auto-reply` endpoint uses MCP to generate contextually appropriate email responses.

## Enhanced MCP Implementation

With the latest update, we've integrated the full MCP Python SDK, which provides a more robust and standardized way to interact with LLMs. The new implementation includes:

### Server Setup

```python
# mcp_server.py
from mcp.server.fastmcp import FastMCP, Context

# Create an MCP server
mcp = FastMCP("FinOfficer")

# Add email processing tools
@mcp.tool()
def analyze_email_tone(email_content: str) -> dict:
    """Analyze the tone of an email"""
    # Implementation
    return {"tone": "professional", "urgency": "medium"}

@mcp.tool()
def generate_email_reply(email_content: str, sender_name: str, tone: str = "professional") -> str:
    """Generate a reply to an email with specified tone"""
    # Implementation
    return f"Dear {sender_name},\n\nThank you for your message...\n\nBest regards,\nFin Officer Team"

# Add company information as a resource
@mcp.resource("company://info")
def get_company_info() -> dict:
    """Get company information"""
    return {
        "name": "Fin Officer",
        "service": "Usługi finansowe i księgowe",
        "contact_email": "contact@finofficer.com",
        "support_email": "support@finofficer.com",
        "website": "https://finofficer.com",
    }

# Add email templates as resources
@mcp.resource("templates://{template_name}")
def get_email_template(template_name: str) -> str:
    """Get an email template by name"""
    templates = {
        "welcome": "Welcome to Fin Officer services...",
        "support": "Thank you for contacting our support team...",
        "followup": "Following up on our previous conversation..."
    }
    return templates.get(template_name, "Template not found")

# Define a prompt for email replies
@mcp.prompt()
def email_reply_prompt(email_content: str, sender_name: str) -> str:
    return f"""You are a customer service representative for Fin Officer.
    Please draft a professional reply to the following email from {sender_name}:
    
    {email_content}
    
    Your reply should be helpful, concise, and end with 'Best regards, Fin Officer Team'."""
```

### Integration with FastAPI

```python
# main.py
from fastapi import FastAPI, Depends, HTTPException
from mcp_server import mcp

app = FastAPI()

# Mount the MCP server to the FastAPI application
app.mount("/mcp", mcp.streamable_http_app())

# Use MCP in an endpoint
@app.post("/api/emails/{email_id}/auto-reply")
async def auto_reply_email(email_id: int):
    # Get email from database
    email = await get_email(email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Use MCP to generate a reply
    reply = await mcp.call_tool(
        "generate_email_reply",
        {
            "email_content": email.content,
            "sender_name": email.sender_name,
            "tone": "professional"
        }
    )
    
    # Send the reply
    await send_email_reply(email_id, reply)
    
    return {"status": "success", "reply": reply}
```

## Benefits of the New MCP Implementation

1. **Standardized Protocol**: Follows the MCP specification for consistent LLM interactions
2. **Separation of Concerns**: Cleanly separates context management from LLM interaction
3. **Resource Management**: Provides a structured way to expose data to LLMs
4. **Tool Integration**: Allows LLMs to call functions in your application
5. **Prompt Templates**: Enables reuse of effective prompting patterns
6. **Transport Flexibility**: Supports multiple transport methods (stdio, SSE, Streamable HTTP)
7. **Authentication**: Supports OAuth 2.0 for secure access to protected resources

## Using MCP CLI Tools

The MCP SDK includes command-line tools for development and testing:

```bash
# Install the MCP server in Claude Desktop
mcp install mcp_server.py

# Test with the MCP Inspector
mcp dev mcp_server.py

# Run the server directly
mcp run mcp_server.py
```

## Advanced Configuration

### Stateful vs. Stateless Servers

```python
# Stateful server (maintains session state)
mcp = FastMCP("StatefulServer")

# Stateless server (no session persistence)
mcp = FastMCP("StatelessServer", stateless_http=True)
```

### Lifespan Management

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass

@dataclass
class AppContext:
    db: Database

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    # Initialize on startup
    db = await Database.connect()
    try:
        yield AppContext(db=db)
    finally:
        # Cleanup on shutdown
        await db.disconnect()

# Pass lifespan to server
mcp = FastMCP("FinOfficer", lifespan=app_lifespan)
```

## Testing MCP Integration

We've implemented comprehensive tests for the MCP functionality:

1. **Unit Tests**: Test individual MCP components (context creation, API calls)
2. **Integration Tests**: Test the interaction between MCP and other services
3. **End-to-End Tests**: Test the complete flow from receiving an email to sending an auto-reply

To run the MCP tests:

```bash
python -m pytest tests/test_mcp_auto_reply_unit.py
python -m pytest tests/test_auto_reply_simple.py
```

## Conclusion

The Model Context Protocol provides a powerful, standardized way to interact with LLMs. By implementing the full MCP specification, our application can now leverage advanced features like resources, tools, and prompts to create more sophisticated and context-aware LLM interactions.
