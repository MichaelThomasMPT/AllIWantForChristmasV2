FROM python:3.12-slim

# Create a working directory
WORKDIR /app

# Install system deps (optional but good hygiene)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the actual app
COPY . /app

# Expose Flask's port
EXPOSE 2025

# Run the app
CMD ["python", "app.py"]
