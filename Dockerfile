# Use Playwright's official Python image (browsers & deps preinstalled)
FROM mcr.microsoft.com/playwright/python:latest

WORKDIR /app

# Copy requirements and install Python packages
COPY Requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r Requirements.txt

# Copy app code
COPY . .

ENV PYTHONUNBUFFERED=1
# Ensure Playwright uses the preinstalled browsers
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Expose a default port (not required but useful)
EXPOSE 10000

# Use PORT env var provided by Render; fallback to 10000 if not set
CMD ["sh", "-lc", "gunicorn -b 0.0.0.0:${PORT:-10000} app:app --workers 2 --threads 4 --log-level info"]
