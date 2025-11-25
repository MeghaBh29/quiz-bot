# Quiz Bot

Automated solver for the "LLM quiz" project. This service accepts POST requests with a JSON payload containing `email`, `secret`, and a `url` to a quiz page. It validates the secret, renders JavaScript pages using Playwright, downloads and parses files (PDF/CSV/Excel/images) if required, computes answers (aggregations, sums, simple analyses), and submits answers to the quiz-provided submit endpoint.

## Features

* Validate incoming requests (400 / 403 handling)
* Render JS-heavy quiz pages using Playwright (headless Chromium)
* Download and parse CSV / Excel / PDF files (pandas, pdfplumber)
* Heuristics to detect submit URLs and post answers
* Modular solver components for easy extension

## Quickstart (local dev)

1. Clone or create the repo and copy files from this project.
2. Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

4. Copy `.env.example` to `.env` and set `QUIZ_SECRET`:

```bash
cp .env.example .env
# edit .env and set QUIZ_SECRET
```

5. Run the Flask app (development):

```bash
export QUIZ_SECRET=your_secret_here
python app.py
```

6. Test the endpoint:

```bash
curl -X POST http://localhost:5000/quiz_endpoint \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","secret":"your_secret_here","url":"https://tds-llm-analysis.s-anand.net/demo"}'
```

## Deployment

For a stable public HTTPS endpoint (required for grading), deploy the repository to a cloud platform:

* Render.com (quick)
* Google Cloud Run
* Heroku
* AWS Fargate / ECS

Set the environment variable `QUIZ_SECRET` on the deployment platform (never commit it to the repo).

## Extending

* Add OCR (Tesseract) for scanned PDFs/images.
* Add more parsing heuristics for differently-structured tables.
* Replace Flask with FastAPI for better async and performance if needed.
* Add queue/workers (Celery/RQ) for scaling.

## License

This project is licensed under the MIT License — see `LICENSE` for details.

## Contact

Create issues / PRs on the GitHub repo or contact the repo owner.
