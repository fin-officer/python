#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Attachment Processing MCP Server

This module implements a Model Context Protocol (MCP) server for processing email attachments.
It provides tools for filtering attachments based on size and file type, analyzing content,
and storing valid attachments in a database.
"""

import json
import logging
import os
import re
import hashlib
import magic
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, BinaryIO
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP, Context, Image
from mcp.server.fastmcp.prompts import base

# Load environment variables
load_dotenv()

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)

# Create an MCP server for attachment processing
mcp_server_name = os.getenv('MCP_ATTACHMENT_SERVER_NAME', 'Fin Officer Attachment Processor')
mcp_server_stateless = os.getenv('MCP_ATTACHMENT_SERVER_STATELESS', 'false').lower() == 'true'

mcp = FastMCP(mcp_server_name, 
             dependencies=["fastapi", "pydantic", "aiohttp", "python-magic"],
             stateless_http=mcp_server_stateless)


# Attachment filtering configuration resource
@mcp.resource("attachment-config://filters")
def get_attachment_filters() -> Dict[str, Any]:
    """Get attachment filtering rules and configuration"""
    # Get blocked extensions from environment variable or use default
    blocked_extensions_str = os.getenv('MCP_BLOCKED_EXTENSIONS', 
                                      '.exe,.bat,.cmd,.sh,.js,.jar,.msi,.dll,.scr,.vbs,.ps1,.tar,.doc')
    blocked_extensions = [ext.strip() for ext in blocked_extensions_str.split(',')]
    
    return {
        "max_size_mb": int(os.getenv('MCP_MAX_ATTACHMENT_SIZE_MB', '10')),
        "blocked_extensions": blocked_extensions,
        "blocked_mime_types": [
            "application/x-msdownload",
            "application/x-executable",
            "application/x-dosexec",
            "application/java-archive",
            "application/x-ms-installer"
        ],
        "scan_for_malware": os.getenv('MCP_SCAN_ATTACHMENTS', 'true').lower() == 'true',
        "extract_text": os.getenv('MCP_EXTRACT_TEXT', 'true').lower() == 'true',
        "storage_path": os.getenv('MCP_ATTACHMENT_STORAGE', '/data/attachments')
    }


# Attachment filtering tool
@mcp.tool()
async def filter_attachment(filename: str, 
                         size_bytes: int,
                         content_type: str = None,
                         content_base64: str = None,
                         ctx: Context = None) -> Dict[str, Any]:
    """Filter an attachment based on size, file type, and content"""
    # Initialize result
    result = {
        "is_allowed": True,
        "rejection_reason": None,
        "file_info": {
            "filename": filename,
            "size_bytes": size_bytes,
            "content_type": content_type,
            "extension": os.path.splitext(filename)[1].lower() if filename else ""
        },
        "analysis": {}
    }
    
    try:
        # Get attachment filters
        if ctx:
            filters, _ = await ctx.read_resource("attachment-config://filters")
        else:
            # Fallback if context is not available
            filters = get_attachment_filters()
        
        # Check file size
        max_size_bytes = filters["max_size_mb"] * 1024 * 1024
        if size_bytes > max_size_bytes:
            result["is_allowed"] = False
            result["rejection_reason"] = f"File size exceeds maximum allowed ({filters['max_size_mb']}MB)"
            return result
        
        # Check file extension
        file_extension = os.path.splitext(filename)[1].lower() if filename else ""
        if file_extension in filters["blocked_extensions"]:
            result["is_allowed"] = False
            result["rejection_reason"] = f"File extension '{file_extension}' is not allowed"
            return result
        
        # Check content type if provided
        if content_type and any(blocked in content_type.lower() for blocked in filters["blocked_mime_types"]):
            result["is_allowed"] = False
            result["rejection_reason"] = f"Content type '{content_type}' is not allowed"
            return result
        
        # If content is provided, perform deeper analysis
        if content_base64:
            try:
                # Decode base64 content
                content = base64.b64decode(content_base64)
                
                # Get actual MIME type using python-magic
                mime = magic.Magic(mime=True)
                detected_type = mime.from_buffer(content)
                result["file_info"]["detected_content_type"] = detected_type
                
                # Check if detected type is blocked
                if any(blocked in detected_type.lower() for blocked in filters["blocked_mime_types"]):
                    result["is_allowed"] = False
                    result["rejection_reason"] = f"Detected content type '{detected_type}' is not allowed"
                    return result
                
                # Calculate file hash for reference
                file_hash = hashlib.sha256(content).hexdigest()
                result["file_info"]["sha256"] = file_hash
                
                # Analyze content if enabled
                if filters["extract_text"] and len(content) < 1024 * 1024:  # Only for files < 1MB
                    text_content = await _extract_text_from_attachment(content, detected_type, filename)
                    if text_content:
                        # Analyze text content with TinyLLM
                        analysis = await _analyze_attachment_content(text_content, filename)
                        result["analysis"] = analysis
            
            except Exception as e:
                logger.error(f"Error analyzing attachment content: {str(e)}")
                # Don't reject the file just because we couldn't analyze it
                result["analysis"]["error"] = str(e)
        
        return result
    
    except Exception as e:
        logger.error(f"Error in attachment filtering: {str(e)}")
        # Default to allowing the file if there's an error in our filtering logic
        result["analysis"]["error"] = str(e)
        return result


# Store attachment tool
@mcp.tool()
async def store_attachment(filename: str,
                         content_base64: str,
                         email_id: str,
                         content_type: str = None,
                         ctx: Context = None) -> Dict[str, Any]:
    """Store an attachment in the database and filesystem"""
    result = {
        "success": False,
        "storage_id": None,
        "file_path": None,
        "error": None
    }
    
    try:
        # Get attachment filters for storage path
        if ctx:
            filters, _ = await ctx.read_resource("attachment-config://filters")
        else:
            # Fallback if context is not available
            filters = get_attachment_filters()
        
        # Decode base64 content
        content = base64.b64decode(content_base64)
        
        # Generate unique ID for the attachment
        file_hash = hashlib.sha256(content).hexdigest()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        storage_id = f"{timestamp}_{file_hash[:8]}"
        
        # Create storage directory if it doesn't exist
        storage_path = filters["storage_path"]
        os.makedirs(storage_path, exist_ok=True)
        
        # Create subdirectory based on date
        date_dir = datetime.now().strftime("%Y-%m-%d")
        storage_subdir = os.path.join(storage_path, date_dir)
        os.makedirs(storage_subdir, exist_ok=True)
        
        # Sanitize filename
        safe_filename = re.sub(r'[^\w\.-]', '_', filename)
        
        # Create file path
        file_path = os.path.join(storage_subdir, f"{storage_id}_{safe_filename}")
        
        # Write file to disk
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Update result
        result["success"] = True
        result["storage_id"] = storage_id
        result["file_path"] = file_path
        result["file_size"] = len(content)
        result["content_type"] = content_type or "application/octet-stream"
        
        # Insert into database (this would typically call a database service)
        # For this example, we'll just log it
        logger.info(f"Stored attachment: {storage_id}, {file_path}, {len(content)} bytes")
        
        return result
    
    except Exception as e:
        logger.error(f"Error storing attachment: {str(e)}")
        result["error"] = str(e)
        return result


# Analyze attachments prompt
@mcp.prompt()
def attachment_analysis_prompt(filename: str, content_snippet: str) -> List[base.Message]:
    """Create a prompt for attachment content analysis"""
    return [
        base.SystemMessage("You are an attachment analysis system. Analyze the content of the file and describe what it contains. "
                          "Focus on identifying potential sensitive information, executable code, or suspicious content."),
        base.UserMessage(f"Filename: {filename}\n\nContent snippet:\n{content_snippet}"),
        base.AssistantMessage("I'll analyze this file content.")
    ]


# Helper function to extract text from attachment
async def _extract_text_from_attachment(content: bytes, content_type: str, filename: str) -> str:
    """Extract text content from an attachment based on its type"""
    try:
        # Simple text extraction for common file types
        if content_type.startswith("text/"):
            # Try different encodings
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    return content.decode(encoding)
                except UnicodeDecodeError:
                    continue
        
        # For PDF, CSV, and other formats, we would use specialized libraries
        # This is a simplified version that returns a preview of binary data
        return f"[Binary content, first 100 bytes: {content[:100].hex()}]"
    
    except Exception as e:
        logger.error(f"Error extracting text from attachment: {str(e)}")
        return f"[Error extracting text: {str(e)}]"


# Helper function to analyze attachment content with TinyLLM
async def _analyze_attachment_content(text_content: str, filename: str) -> Dict[str, Any]:
    """Use TinyLLM to analyze attachment content"""
    try:
        import httpx
        
        # Get TinyLLM API URL and model from environment variables
        api_url = os.getenv("LLM_API_URL", "http://tinyllm:11434")
        model = os.getenv("LLM_MODEL", "llama2")
        
        # Limit text content to a reasonable size
        max_content_length = 1000
        content_snippet = text_content[:max_content_length]
        if len(text_content) > max_content_length:
            content_snippet += "\n[Content truncated...]"
        
        # Create prompt for content analysis
        prompt = f"""
        You are an attachment analysis system. Analyze the following file content and provide:
        1. A brief description of what the file contains
        2. Any potential sensitive information detected
        3. Any suspicious elements or security concerns
        4. A risk assessment (Low, Medium, High)
        
        Filename: {filename}
        
        Content snippet:
        {content_snippet}
        
        Respond in JSON format with the following structure:
        {{
          "description": "Brief description of file contents",
          "sensitive_info": ["list", "of", "sensitive", "information", "detected"],
          "security_concerns": ["list", "of", "security", "concerns"],
          "risk_level": "Low/Medium/High"
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
                    # If JSON parsing fails, return the raw response
                    return {"raw_analysis": llm_response}
            
            # Default response if API call fails
            return {"error": f"Error calling TinyLLM API: {response.status_code}"}
    
    except Exception as e:
        logger.error(f"Error in TinyLLM analysis: {str(e)}")
        return {"error": str(e)}


# Run the server if executed directly
if __name__ == "__main__":
    # Get transport and mount path from environment variables
    transport = os.getenv('MCP_ATTACHMENT_TRANSPORT', 'streamable-http')
    mount_path = os.getenv('MCP_ATTACHMENT_MOUNT_PATH', '/mcp/attachments')
    
    # Run the server with configured settings
    mcp.run(transport=transport, mount_path=mount_path)
