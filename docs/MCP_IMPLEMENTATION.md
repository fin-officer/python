# Model Context Protocol (MCP) Implementation Guide

## Overview

This document provides a comprehensive guide to the Model Context Protocol (MCP) implementation in the Fin Officer application. The MCP integration enables standardized communication with language models, providing a robust framework for auto-reply functionality and other LLM-based features.

## Implementation Details

### Components

1. **MCP Server** (`app/mcp_server.py`)
   - Implements the FastMCP server with resources, tools, and prompts
   - Configurable via environment variables
   - Provides standardized access to company information and email templates

2. **MCP Integration** (`app/mcp_integration.py`)
   - Integrates the MCP server with the FastAPI application
   - Provides endpoints for email processing, resource listing, and prompt generation
   - Demonstrates how to use MCP tools and resources in a real application

3. **Ansible Tests** (`ansible/mcp_tests.yml`)
   - Verifies the MCP implementation through automated tests
   - Tests auto-reply functionality, resource access, and tool availability

### Environment Variables

The MCP implementation uses the following environment variables for configuration:

```
# MCP Configuration
MCP_SERVER_NAME="Fin Officer MCP"
MCP_SERVER_STATELESS=false
MCP_COMPANY_NAME="Fin Officer"
MCP_COMPANY_SERVICE="Usługi finansowe i księgowe"
MCP_COMPANY_CONTACT_EMAIL=contact@finofficer.com
MCP_COMPANY_SUPPORT_EMAIL=support@finofficer.com
MCP_COMPANY_WEBSITE=https://finofficer.com
MCP_MOUNT_PATH=/mcp
MCP_TRANSPORT=streamable-http
```

## Setup and Configuration

### Dependencies

The MCP implementation requires the following dependencies:

```
mcp==1.9.0  # Using the latest available version for MCP specification support
python-dotenv==1.0.0
fastapi==0.88.0
pydantic==1.10.8
uvicorn==0.23.2
```

Install these dependencies using:

```bash
pip install -r requirements.txt
```

### Configuration

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Customize the MCP configuration in the `.env` file as needed.

## Running the MCP Server

### Standalone Mode

To run the MCP server in standalone mode:

```bash
python app/mcp_server.py
```

This will start the MCP server using the configured transport (default: streamable-http) and mount path (default: /mcp).

### Integrated with FastAPI

To run the MCP server integrated with the FastAPI application:

```bash
python app/mcp_integration.py
```

This will start the FastAPI application with the MCP server mounted at the configured path.

## Using MCP in the Application

### Auto-Reply Functionality

The MCP implementation provides auto-reply functionality through the `/api/emails/process-mcp` endpoint. This endpoint uses MCP tools to analyze email tone and generate appropriate responses.

Example request:

```json
{
  "sender": "John Doe",
  "sender_email": "john.doe@example.com",
  "subject": "Question about services",
  "content": "Hello, I'm interested in your financial services. Could you provide more information about your accounting packages?",
  "attachment_ids": []
}
```

Example response:

```json
{
  "status": "success",
  "reply": "Szanowny/a John Doe,\n\nDziękujemy za kontakt z Fin Officer. Potwierdzamy otrzymanie Pana/Pani wiadomości i zapewniamy, że zostanie ona rozpatrzona w najkrótszym możliwym terminie.\n\nZ poważaniem,\nZespół Fin Officer",
  "tone_analysis": {
    "tone": "professional",
    "urgency": "medium",
    "sentiment": "neutral",
    "key_topics": ["accounting", "services", "information"]
  }
}
```

### MCP Resources

The MCP server provides the following resources:

1. **Company Information** (`company://info`)
   - Provides basic company information like name, service, and contact details
   - Configurable via environment variables

2. **Email Templates** (`templates://{template_name}`)
   - Provides email templates for different scenarios (welcome, support, followup)
   - Templates can be loaded from files or use default values

### MCP Tools

The MCP server provides the following tools:

1. **Email Tone Analysis** (`analyze_email_tone`)
   - Analyzes the tone and urgency of an email
   - Returns tone, urgency, sentiment, and key topics

2. **Email Reply Generation** (`generate_email_reply`)
   - Generates a reply to an email with specified parameters
   - Customizable tone and greeting

3. **Email History** (`get_email_history`)
   - Retrieves conversation history with a specific email address
   - Useful for providing context in auto-replies

## Testing

### Running Tests

To test the MCP implementation using Ansible:

```bash
cd ansible
ansible-playbook mcp_tests.yml
```

This will run a series of tests to verify that the MCP server is properly configured and functioning as expected.

### Test Scenarios

1. **Auto-Reply Functionality**
   - Tests the `/api/emails/process-mcp` endpoint
   - Verifies that the generated reply contains the company name

2. **MCP Resources**
   - Tests the `/api/mcp/resources` endpoint
   - Verifies that resources are available and accessible

3. **MCP Tools**
   - Tests the `/api/mcp/tools` endpoint
   - Verifies that tools are available and accessible

4. **Email Reply Prompt**
   - Tests the `/api/prompts/email-reply` endpoint
   - Verifies that prompts are generated correctly

## Troubleshooting

### Common Issues

1. **Missing Dependencies**
   - Ensure all required packages are installed: `pip install -r requirements.txt`
   - If using a virtual environment, make sure it's activated

2. **Configuration Issues**
   - Check that the `.env` file exists and contains the correct configuration
   - Verify that environment variables are being loaded correctly

3. **Server Not Starting**
   - Check for error messages in the console output
   - Verify that the required ports are available

4. **MCP Server Not Mounted**
   - Check the `MCP_MOUNT_PATH` environment variable
   - Verify that the MCP server is properly mounted in the FastAPI application

## Extending the MCP Implementation

### Adding New Resources

To add a new resource to the MCP server:

```python
@mcp.resource("new-resource://{param}")\ndef get_new_resource(param: str) -> Dict[str, Any]:\n    """Get a new resource"""\n    # Implementation\n    return {"param": param, "data": "Some data"}
```

### Adding New Tools

To add a new tool to the MCP server:

```python
@mcp.tool()\ndef new_tool(param1: str, param2: int) -> str:\n    """A new tool"""\n    # Implementation\n    return f"Processed {param1} with {param2}"
```

### Adding New Prompts

To add a new prompt to the MCP server:

```python
@mcp.prompt()\ndef new_prompt(param: str) -> List[base.Message]:\n    """A new prompt"""\n    return [\n        base.SystemMessage("System message"),\n        base.UserMessage(f"User message with {param}"),\n        base.AssistantMessage("Assistant message")\n    ]
```

## Conclusion

The Model Context Protocol implementation provides a powerful framework for integrating language models into the Fin Officer application. By using MCP, we achieve a standardized approach to context management, resource access, and tool execution, making it easier to build sophisticated LLM-powered features.
