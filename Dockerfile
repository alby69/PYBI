FROM python:3.11-slim

WORKDIR /app

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Upgrade pip and install dependencies with retries
COPY requirements.txt .

RUN pip install --upgrade pip --no-cache-dir && \
    pip install --no-cache-dir --default-timeout=120 --retries=10 -r requirements.txt

# Copy application files
COPY . .

# Expose NiceGUI port
EXPOSE 8080

# Run PyBI application
CMD ["python", "-m", "pybi.main", "--host", "0.0.0.0", "--port", "8080"]