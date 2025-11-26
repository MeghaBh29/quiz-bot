FROM mcr.microsoft.com/playwright/python:latest

WORKDIR /app

COPY Requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r Requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
EXPOSE 10000

CMD ["sh", "-c", "python -m gunicorn -b 0.0.0.0:${PORT:-10000} app:app --workers 2 --threads 4 --log-level info"]
