#!/usr/bin/env python3

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.db_service import EmailTable
from app.services.email_service import EmailService
from app.services.llm_service import LlmService


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def mock_db_record():
    """Create a mock database record"""
    record = AsyncMock(spec=EmailTable)
    record.id = 1
    record.from_email = "test@example.com"
    record.to_email = "support@finofficer.com"
    record.subject = "Test Subject"
    record.content = "Test Content"
    record.received_date = "2025-05-20T00:00:00"
    return record


@pytest.mark.asyncio
async def test_auto_reply_endpoint(test_client, mock_db_record):
    """Test the auto-reply endpoint"""
    # Mock database query
    with (
        patch("sqlalchemy.ext.asyncio.AsyncSession.execute") as mock_execute,
        patch("app.services.llm_service.LlmService.generate_auto_reply") as mock_generate,
        patch("app.services.email_service.EmailService.reply_to_email") as mock_reply,
        patch("app.services.db_service.get_email_history") as mock_history,
    ):

        # Configure mocks
        mock_result = AsyncMock()
        mock_result.scalars.return_value.first.return_value = mock_db_record
        mock_execute.return_value = mock_result

        mock_generate.return_value = "Auto-generated reply content"
        mock_reply.return_value = True
        mock_history.return_value = []

        # Make the request
        response = test_client.post("/api/emails/1/auto-reply")

        # Assert response
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert "Auto-generated reply content" in response.json()["content"]

        # Verify mocks were called
        assert mock_execute.called
        assert mock_generate.called
        assert mock_reply.called
        assert mock_history.called


@pytest.mark.asyncio
async def test_auto_reply_endpoint_not_found(test_client):
    """Test the auto-reply endpoint when email is not found"""
    # Mock database query to return None
    with patch("sqlalchemy.ext.asyncio.AsyncSession.execute") as mock_execute:
        mock_result = AsyncMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_execute.return_value = mock_result

        # Make the request
        response = test_client.post("/api/emails/999/auto-reply")

        # Assert response
        assert response.status_code == 404
        assert "nie znaleziona" in response.json()["detail"]


@pytest.mark.asyncio
async def test_auto_reply_endpoint_background_task(test_client, mock_db_record):
    """Test the auto-reply endpoint with background task"""
    # Mock database query
    with (
        patch("sqlalchemy.ext.asyncio.AsyncSession.execute") as mock_execute,
        patch("app.services.llm_service.LlmService.generate_auto_reply") as mock_generate,
        patch("fastapi.BackgroundTasks.add_task") as mock_add_task,
        patch("app.services.db_service.get_email_history") as mock_history,
    ):

        # Configure mocks
        mock_result = AsyncMock()
        mock_result.scalars.return_value.first.return_value = mock_db_record
        mock_execute.return_value = mock_result

        mock_generate.return_value = "Auto-generated reply content"
        mock_history.return_value = []

        # Make the request with background=true query parameter
        response = test_client.post("/api/emails/1/auto-reply?background=true")

        # Assert response
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert "w tle" in response.json()["message"]

        # Verify background task was added
        assert mock_add_task.called
