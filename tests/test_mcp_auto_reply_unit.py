#!/usr/bin/env python3

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import EmailSchema, Emotion, Formality, Sentiment, ToneAnalysis, Urgency
from app.services.llm_service import LlmService


@pytest.fixture
def mock_response():
    """Mock response from the LLM API"""
    return {
        "response": "Szanowny/a Test,\n\nDziękujemy za zainteresowanie naszymi usługami finansowymi. Oferujemy pakiety księgowe dostosowane do małych firm, które obejmują miesięczną księgowość oraz rozliczenia podatkowe.\n\nZapraszamy do kontaktu telefonicznego, aby omówić szczegóły.\n\nZ poważaniem,\nZespół Fin Officer"
    }


@pytest.fixture
def sample_email():
    """Sample email for testing"""
    return EmailSchema(
        id=1,
        from_email="test@example.com",
        to_email="support@fin-officer.com",
        subject="Question about financial services",
        content="Hello,\n\nI am interested in your financial services. Could you please provide more information about your accounting packages for small businesses? I currently have 5 employees and need help with monthly bookkeeping and tax filing.\n\nThank you,\nJohn",
        received_date="2025-05-20T00:40:00",
    )


@pytest.mark.asyncio
async def test_generate_auto_reply(mock_response, sample_email):
    """Test the generate_auto_reply method"""
    # Arrange
    llm_service = LlmService()

    # Mock the API call
    with patch.object(
        llm_service, "_call_llm_api_with_mcp", new_callable=AsyncMock
    ) as mock_call_api:
        mock_call_api.return_value = mock_response["response"]

        # Act
        result = await llm_service.generate_auto_reply(
            email_content=sample_email.content, sender_name="Test", email_history=[]
        )

        # Assert
        assert "Dziękujemy za zainteresowanie" in result
        assert "Zespół Fin Officer" in result
        assert mock_call_api.called

        # Verify that the MCP context was created correctly
        call_args = mock_call_api.call_args[0][0]
        assert "context" in call_args
        assert "instructions" in call_args
        assert call_args["context"]["sender"]["name"] == "Test"
        assert sample_email.content in call_args["context"]["email"]["content"]


@pytest.mark.asyncio
async def test_create_mcp_context(sample_email):
    """Test the _create_mcp_context method"""
    # Arrange
    llm_service = LlmService()
    sender_name = "Test"
    email_history = [
        {"from_user": True, "content": "Previous question", "timestamp": "2025-05-19T00:00:00"},
        {"from_user": False, "content": "Previous answer", "timestamp": "2025-05-19T00:01:00"},
    ]

    # Act
    context = llm_service._create_mcp_context(
        email_content=sample_email.content, sender_name=sender_name, email_history=email_history
    )

    # Assert
    assert context["context"]["sender"]["name"] == sender_name
    assert context["context"]["email"]["content"] == sample_email.content
    assert len(context["context"]["conversation_history"]) == 2
    assert context["context"]["company"]["name"] == "Fin Officer"
    assert len(context["instructions"]) > 0
    assert context["output_format"] == "text"


@pytest.mark.asyncio
async def test_call_llm_api_with_mcp(mock_response):
    """Test the _call_llm_api_with_mcp method"""
    # Arrange
    llm_service = LlmService()
    mcp_context = {
        "context": {"test": "value"},
        "instructions": ["instruction1", "instruction2"],
        "output_format": "text",
    }

    # Mock the aiohttp ClientSession
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.post.return_value.__aenter__.return_value.status = 200
    mock_session.post.return_value.__aenter__.return_value.json = AsyncMock(
        return_value=mock_response
    )

    # Act
    with patch("aiohttp.ClientSession", return_value=mock_session):
        result = await llm_service._call_llm_api_with_mcp(mcp_context)

    # Assert
    assert result == mock_response["response"]
    assert mock_session.post.called
    payload = mock_session.post.call_args[1]["json"]
    assert payload["model"] == llm_service.model
    assert "<mcp>" in payload["prompt"]
    assert json.dumps(mcp_context) in payload["prompt"]


@pytest.mark.asyncio
async def test_default_reply():
    """Test the _create_default_reply method"""
    # Arrange
    llm_service = LlmService()
    sender_name = "Test"

    # Act
    result = llm_service._create_default_reply(sender_name)

    # Assert
    assert sender_name in result
    assert "Dziękujemy za wiadomość" in result
    assert "Zespół Fin Officer" in result
