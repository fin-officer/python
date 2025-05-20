#!/usr/bin/env python3

"""
Simplified tests for the auto-reply functionality
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.mocks import EmailSchema, LlmService


@pytest.fixture
def sample_email():
    """Create a sample email for testing"""
    return EmailSchema(
        id=1,
        from_email="test@example.com",
        to_email="support@finofficer.com",
        subject="Question about financial services",
        content="Hello,\n\nI am interested in your financial services.",
        received_date="2025-05-20T00:40:00",
    )


@pytest.mark.asyncio
async def test_generate_auto_reply():
    """Test the generate_auto_reply method"""
    # Arrange
    llm_service = LlmService()
    email_content = "Hello, I have a question about your services."
    sender_name = "Test"

    # Act
    result = await llm_service.generate_auto_reply(
        email_content=email_content, sender_name=sender_name, email_history=[]
    )

    # Assert
    assert result is not None
    assert sender_name in result
    assert "Thank you" in result


@pytest.mark.asyncio
async def test_create_mcp_context():
    """Test the _create_mcp_context method"""
    # Arrange
    llm_service = LlmService()
    email_content = "Hello, I have a question about your services."
    sender_name = "Test"

    # Act
    context = llm_service._create_mcp_context(
        email_content=email_content, sender_name=sender_name, email_history=[]
    )

    # Assert
    assert context is not None
    assert "context" in context
    assert context["context"]["sender"]["name"] == sender_name
    assert context["context"]["email"]["content"] == email_content
