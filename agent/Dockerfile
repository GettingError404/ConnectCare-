FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    portaudio19-dev \
    espeak \
    libespeak-dev \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create model directory
RUN mkdir -p /app/models/vosk

# Expose API port
EXPOSE 8000

# Default to API mode
CMD ["python", "main.py", "api"]
