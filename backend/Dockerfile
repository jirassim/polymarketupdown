FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY . .

# Create data and logs directories
RUN mkdir -p /app/data /app/logs

# Expose port
EXPOSE 5000

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000", "--reload"]