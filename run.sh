#!/bin/bash

# Set up environment variables from .env file if it exists
if [ -f .env ]; then
  export $(cat .env | grep -v '^#' | xargs)
fi

# Create required directories
mkdir -p data/templates data/archive logs

# Check if .env file exists, if not create from example
if [ ! -f .env ]; then
  echo "Creating .env file from .env.example..."
  cp .env.example .env
fi

# Print startup message
echo "Starting Email LLM Processor..."
echo "Python implementation with FastAPI and FastMCP"

# Print configuration
echo "
Configuration:"
echo "- Email Host: ${EMAIL_HOST:-mailhog}"
echo "- Email Port: ${EMAIL_PORT:-1025}"
echo "- LLM API URL: ${LLM_API_URL:-http://localhost:11434}"
echo "- LLM Model: ${LLM_MODEL:-llama2}"
echo "- Database URL: ${DATABASE_URL:-sqlite:///data/emails.db}"
echo "- Template Directory: ${TEMPLATE_DIR:-/data/templates}"
echo "- Archive Directory: ${ARCHIVE_DIR:-/data/archive}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "
WARNING: Docker is not running or not installed.
If you're using Docker, please start Docker first.
If you're running without Docker, make sure all dependencies are installed.
"
  sleep 2
fi

# Build and start services with Docker Compose
echo "
Starting services with Docker Compose..."
docker-compose up -d --build

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 5

# Check if containers are running
if docker-compose ps | grep -q "Up"; then
  echo "Docker containers are running!"
else
  echo "WARNING: Some containers might not be running. Check with 'docker-compose ps'"
fi

# Provide instructions for testing
echo "
=========================================================================================
Email LLM Processor (Python FastAPI) is running!
=========================================================================================

- FastAPI application: http://localhost:8000
- FastAPI Swagger docs: http://localhost:8000/docs
- MailHog (test email server): http://localhost:8025
- Adminer (database management): http://localhost:8081

To test the application, you can:
1. Open Swagger documentation at http://localhost:8000/docs
2. Send an email to ${EMAIL_USER:-test@example.com} using MailHog
3. Use the API to send a test email:
   curl -X POST \"http://localhost:8000/api/emails/send-test?to_email=user@example.com\"
4. Process an email manually:
   curl -X POST \"http://localhost:8000/api/emails/process\" \\
     -H \"Content-Type: application/json\" \\
     -d '{
       \"from_email\": \"test@example.com\",
       \"to_email\": \"${EMAIL_USER:-test@example.com}\",
       \"subject\": \"Test wiadomości\",
       \"content\": \"To jest testowa wiadomość do przetworzenia przez system.\"
     }'

Available templates:
- default.template: Standard response
- frequent_sender.template: Response for frequent senders
- negative_repeated.template: Response for repeated negative feedback
- urgent_critical.template: Response for urgent messages

You can view templates with:
curl http://localhost:8000/api/templates

To stop the application, press Ctrl+C or run 'docker-compose down'
=========================================================================================
"

# Show logs
echo "Showing logs from the application container (Ctrl+C to stop viewing logs):"
docker-compose logs -f app