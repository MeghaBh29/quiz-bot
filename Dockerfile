FROM python:3.11-slim

# Install system packages needed by Chromium / Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates wget gnupg \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxss1 libasound2 libgbm1 \
    libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 \
    libxfixes3 libxi6 libxrandr2 libxrender1 libgtk-3-0 libglib2.0-0 libgdk-pixbuf2.0-0 \
    libc6 libcairo2 libdbus-1-3 libpango-1.0-0 libgcc1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY Requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN python -m playwright install chromium

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Use gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app", "--workers", "2", "--threads", "4"]
