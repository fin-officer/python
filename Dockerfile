FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create directories for data with proper permissions
RUN mkdir -p /data/templates /data/archive && chmod -R 777 /data

# Install Python dependencies individually to avoid conflicts
RUN pip install --upgrade pip && \
    pip install fastapi==0.88.0 && \
    pip install pydantic==1.10.8 && \
    pip install uvicorn==0.23.2 && \
    pip install click && \
    pip install sqlalchemy==2.0.21 && \
    pip install aiosmtplib==2.0.2 && \
    pip install aioimaplib==1.0.1 && \
    pip install python-dotenv==1.0.0 && \
    pip install email-validator==2.0.0.post2 && \
    pip install jinja2==3.1.2 && \
    pip install aiosqlite==0.19.0 && \
    pip install python-multipart==0.0.6 && \
    pip install httpx==0.24.1 && \
    pip install email-reply-parser==0.5.12 && \
    pip install schedule==1.2.0 && \
    pip install apscheduler==3.10.4 && \
    pip install fastapi-utils==0.2.1 && \
    pip install python-dateutil==2.8.2 && \
    pip install aiohttp==3.8.5

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