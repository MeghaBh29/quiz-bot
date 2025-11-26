# Use Playwright image that matches the python playwright package installed
FROM mcr.microsoft.com/playwright/python:v1.56.0-jammy

WORKDIR /app

# Copy requirements and install Python packages
COPY Requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r Requirements.txt

# Copy app code
COPY . .

ENV PYTHONUNBUFFERED=1
# Use the preinstalled browsers from the base image
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Expose default port (Render provides $PORT)
EXPOSE 10000

# Start server using python -m gunicorn to avoid PATH issues
CMD ["sh", "-c", "python -m gunicorn -b 0.0.0.0:${PORT:-10000} app:app --workers 2 --threads 4 --log-level info"]
