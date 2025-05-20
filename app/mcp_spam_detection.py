#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Spam Detection MCP Server

This module implements a Model Context Protocol (MCP) server for spam detection
using TinyLLM. It provides tools and resources for evaluating whether an email
is spam based on its content, sender, and other attributes.
"""

import json
import logging
import os
import re
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

# Create an MCP server for spam detection
mcp_server_name = os.getenv('MCP_SPAM_SERVER_NAME', 'Fin Officer Spam Detection')
mcp_server_stateless = os.getenv('MCP_SPAM_SERVER_STATELESS', 'false').lower() == 'true'

mcp = FastMCP(mcp_server_name, 
             dependencies=["fastapi", "pydantic", "aiohttp"],
             stateless_http=mcp_server_stateless)


# Spam detection configuration resource
@mcp.resource("spam-config://rules")
def get_spam_rules() -> Dict[str, Any]:
    """Get spam detection rules and configuration"""
    return {
        "spam_keywords": [
            "viagra", "lottery", "winner", "million dollars", "nigerian prince",
            "inheritance", "bank transfer", "urgent attention", "confidential business",
            "investment opportunity", "cryptocurrency offer", "extend warranty"
        ],
        "suspicious_tlds": [".xyz", ".top", ".loan", ".work", ".click", ".link"],
        "min_spam_score": 0.7,  # Threshold for classifying as spam
        "check_spf": True,      # Check SPF records
        "check_dkim": True,     # Check DKIM signatures
        "check_dmarc": True,    # Check DMARC policy
        "max_links": 5,         # Maximum number of links before suspicious
        "max_image_count": 3    # Maximum number of images before suspicious
    }


# Spam detection whitelist resource
@mcp.resource("spam-config://whitelist")
def get_whitelist() -> List[str]:
    """Get whitelist of trusted email domains and addresses"""
    # Get whitelist from environment variable or use default
    whitelist_str = os.getenv('MCP_SPAM_WHITELIST', 'finofficer.com,trusted-partner.com')
    whitelist = [domain.strip() for domain in whitelist_str.split(',')]
    return whitelist


# Spam detection tool
@mcp.tool()
async def detect_spam(email_content: str, 
                   sender_email: str,
                   subject: str,
                   has_attachments: bool = False,
                   ctx: Context = None) -> Dict[str, Any]:
    """Detect if an email is spam based on content and metadata"""
    # Initialize result
    result = {
        "is_spam": False,
        "spam_score": 0.0,
        "spam_indicators": [],
        "analysis": ""
    }
    
    try:
        # Get spam rules and whitelist
        if ctx:
            spam_rules, _ = await ctx.read_resource("spam-config://rules")
            whitelist, _ = await ctx.read_resource("spam-config://whitelist")
        else:
            # Fallback if context is not available
            spam_rules = get_spam_rules()
            whitelist = get_whitelist()
        
        # Check if sender is in whitelist
        for trusted_domain in whitelist:
            if trusted_domain in sender_email:
                result["analysis"] = f"Email from trusted domain: {trusted_domain}"
                return result
        
        # Basic spam indicators
        spam_indicators = []
        spam_score = 0.0
        
        # Check for spam keywords in subject and content
        for keyword in spam_rules["spam_keywords"]:
            if keyword.lower() in subject.lower() or keyword.lower() in email_content.lower():
                spam_indicators.append(f"Contains spam keyword: {keyword}")
                spam_score += 0.1
        
        # Check for suspicious TLDs
        for tld in spam_rules["suspicious_tlds"]:
            if tld in sender_email:
                spam_indicators.append(f"Suspicious sender TLD: {tld}")
                spam_score += 0.2
        
        # Check for excessive capitalization
        caps_ratio = sum(1 for c in subject if c.isupper()) / max(len(subject), 1)
        if caps_ratio > 0.5:
            spam_indicators.append("Excessive capitalization in subject")
            spam_score += 0.1
        
        # Check for multiple exclamation marks
        if subject.count('!') > 2 or email_content.count('!') > 5:
            spam_indicators.append("Multiple exclamation marks")
            spam_score += 0.1
        
        # Check for excessive links
        link_count = len(re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', email_content))
        if link_count > spam_rules["max_links"]:
            spam_indicators.append(f"Excessive links: {link_count}")
            spam_score += 0.2
        
        # Check for attachments (if suspicious)
        if has_attachments:
            spam_score += 0.1
            spam_indicators.append("Contains attachments")
        
        # Use TinyLLM for advanced spam detection
        llm_spam_score = await _analyze_with_tinyllm(email_content, subject, sender_email)
        spam_score += llm_spam_score * 0.5  # Weight the LLM score at 50%
        
        # Determine if it's spam based on score
        if spam_score >= spam_rules["min_spam_score"]:
            result["is_spam"] = True
        
        # Update result
        result["spam_score"] = min(spam_score, 1.0)  # Cap at 1.0
        result["spam_indicators"] = spam_indicators
        result["analysis"] = f"Spam score: {result['spam_score']:.2f}, Indicators: {len(spam_indicators)}"
        
        return result
    
    except Exception as e:
        logger.error(f"Error in spam detection: {str(e)}")
        result["analysis"] = f"Error in spam detection: {str(e)}"
        return result


# Spam classification prompt
@mcp.prompt()
def spam_detection_prompt(email_content: str, subject: str, sender: str) -> List[base.Message]:
    """Create a prompt for spam detection"""
    return [
        base.SystemMessage("You are a spam detection system. Analyze the email and determine if it's spam. "
                          "Respond with a spam score between 0.0 (definitely not spam) and 1.0 (definitely spam)."),
        base.UserMessage(f"From: {sender}\nSubject: {subject}\n\n{email_content}"),
        base.AssistantMessage("I'll analyze this email for spam indicators.")
    ]


# Helper function to analyze email with TinyLLM
async def _analyze_with_tinyllm(email_content: str, subject: str, sender_email: str) -> float:
    """Use TinyLLM to analyze email content for spam indicators"""
    try:
        import httpx
        
        # Get TinyLLM API URL and model from environment variables
        api_url = os.getenv("LLM_API_URL", "http://tinyllm:11434")
        model = os.getenv("LLM_MODEL", "llama2")
        
        # Create prompt for spam detection
        prompt = f"""
        You are a spam detection system. Analyze the following email and determine if it's spam.
        Respond with a single number between 0.0 (definitely not spam) and 1.0 (definitely spam).
        
        From: {sender_email}
        Subject: {subject}
        
        {email_content}
        
        Spam score (0.0 to 1.0):
        """
        
        # Call TinyLLM API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "temperature": 0.1,  # Low temperature for more deterministic results
                    "max_tokens": 10,   # We only need a short response
                    "stream": False
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                # Extract numeric score from response
                score_text = result.get("response", "0.5").strip()
                # Find the first floating point number in the response
                match = re.search(r'\d+\.\d+', score_text)
                if match:
                    return float(match.group(0))
                # If no decimal found, look for integer
                match = re.search(r'\d+', score_text)
                if match:
                    return float(match.group(0))
                # Default fallback
                return 0.5
            else:
                logger.error(f"Error calling TinyLLM API: {response.status_code}")
                return 0.5  # Default moderate score on error
    
    except Exception as e:
        logger.error(f"Error in TinyLLM analysis: {str(e)}")
        return 0.5  # Default moderate score on error


# Run the server if executed directly
if __name__ == "__main__":
    # Get transport and mount path from environment variables
    transport = os.getenv('MCP_SPAM_TRANSPORT', 'streamable-http')
    mount_path = os.getenv('MCP_SPAM_MOUNT_PATH', '/mcp/spam')
    
    # Run the server with configured settings
    mcp.run(transport=transport, mount_path=mount_path)
