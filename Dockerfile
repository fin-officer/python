FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create directories for data with proper permissions
RUN mkdir -p /data/templates /data/archive && chmod -R 777 /data

# Copy requirements file
COPY ./requirements.txt /app/

# Install Python dependencies from requirements.txt
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    # Explicitly install MCP package to ensure it's available
    pip install mcp==1.9.0 && \
    # Install additional dependencies for attachment processing
    pip install python-magic==0.4.27 filetype==1.2.0 pillow==10.0.0 pyPDF2==3.0.1 chardet==5.1.0

# Copy application code
COPY ./app /app/

# Verify email_service.py exists and contains EmailService class
RUN ls -la /app/services/ && \
    cat /app/services/email_service.py | grep -q 'class EmailService' && \
    echo 'EmailService class found in email_service.py'

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]