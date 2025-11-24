FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY start_agent.py .

# Set Python path
ENV PYTHONPATH=/app

# Run the agent (LiveKit Cloud will call this directly)
# cli.run_app() handles both 'dev' and 'start' commands internally
CMD ["python", "start_agent.py"]
