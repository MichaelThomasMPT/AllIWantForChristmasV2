FROM python:3.12-slim

# Create a working directory
WORKDIR /app

# Pick up any Debian security fixes released since the base image was built,
# plus CA certificates for the outbound reverse-geocoding requests.
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the actual app
COPY . /app

# Expose the app's port
EXPOSE 2025

# Serve with gunicorn rather than Flask's development server, which must not
# face the internet. One worker keeps CSV appends from different processes
# from interleaving; threads handle concurrent requests.
CMD ["gunicorn", "--workers", "1", "--threads", "4", "--bind", "0.0.0.0:2025", "--access-logfile", "-", "app:app"]
