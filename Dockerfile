# Use Playwright's official Python image which has browsers & deps preinstalled
FROM mcr.microsoft.com/playwright/python:latest

# Create app dir
WORKDIR /app

# Copy requirements and install Python packages
COPY Requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r Requirements.txt

# Copy application code
COPY . .

# Expose same port your app uses
EXPOSE 10000

# Ensure Playwright browsers path (optional)
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Run gunicorn (production WSGI)
CMD ["gunicorn", "-b", "0.0.0.0:10000", "app:app", "--workers", "2", "--threads", "4"]
