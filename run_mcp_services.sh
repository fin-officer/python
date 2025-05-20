#!/bin/bash

# Script to run all MCP services for the Fin Officer application

echo "Starting MCP services for Fin Officer..."

# Create necessary directories
mkdir -p data/attachments
mkdir -p data/emails

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "Error: Docker is not running. Please start Docker and try again."
  exit 1
fi

# Pull the latest changes
echo "Pulling the latest changes..."
git pull

# Build and start the services
echo "Building and starting the services..."
docker-compose down
docker-compose build
docker-compose up -d

# Wait for services to start
echo "Waiting for services to start..."
sleep 10

# Check if services are running
echo "Checking if services are running..."
docker-compose ps

# Run the tests
echo "Running MCP integration tests..."
cd ansible
ansible-playbook mcp_tests.yml

echo "MCP services are now running. You can access the following endpoints:"
echo "- Main Application: http://localhost:8000"
echo "- Email Processor MCP: http://localhost:8001/mcp/email"
echo "- Spam Detector MCP: http://localhost:8002/mcp/spam"
echo "- Attachment Processor MCP: http://localhost:8003/mcp/attachments"
echo "- MailHog (Email Testing): http://localhost:8025"
echo "- Adminer (Database): http://localhost:8081"

echo "To stop the services, run: docker-compose down"
