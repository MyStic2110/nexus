# Base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Metadata
ENV PYTHONUNBUFFERED=1

# Expose port (FastAPI default)
EXPOSE 8000

# Make startup script executable
RUN chmod +x start.sh

# Start both API + Cricbuzz Surveillance Agent
CMD ["bash", "start.sh"]
