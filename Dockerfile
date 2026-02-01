# Use the official Python image from the Docker Hub
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libpoppler-cpp-dev \
    pkg-config \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Create directory for temporary files
RUN mkdir -p /data/temp && \
    chmod 777 /data/temp

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV TEMP_DIR=/data/temp

# Expose the port
EXPOSE 8000

# Command to run the API server
CMD ["python", "main.py", "serve", "--host", "0.0.0.0", "--port", "8000"]