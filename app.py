# app.py
import os
import asyncio
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# local dev .env loader (safe to keep; .env should not be committed)
load_dotenv()

# Flask app
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Config from environment (defaults for local dev)
QUIZ_SECRET = os.environ.get("QUIZ_SECRET", "s3cr3t-for-quiz-XYZ")
BROWSER_TIMEOUT = int(os.environ.get("BROWSER_TIMEOUT", "180"))  # seconds
MAX_STEPS = int(os.environ.get("MAX_STEPS", "6"))  # max chained pages

# Import async workflow after app/config so imports succeed
from solver.analysis import process_quiz_workflow

@app.route("/", methods=["GET"])
def health():
    return {
        "status": "ok",
        "service": "quiz-bot",
        "note": "POST to /quiz_endpoint with {email,secret,url}"
    }, 200


@app.route("/quiz_endpoint", methods=["POST"])
def quiz_endpoint():
    # Validate JSON
    if not request.is_json:
        return jsonify({"error": "invalid json"}), 400

    try:
        payload = request.get_json()
    except Exception:
        return jsonify({"error": "invalid json"}), 400

    email = payload.get("email")
    secret = payload.get("secret")
    url = payload.get("url")

    if not email or not secret or not url:
        return jsonify({"error": "missing fields"}), 400

    # Use QUIZ_SECRET (env var name)
    if secret != QUIZ_SECRET:
        return jsonify({"error": "invalid secret"}), 403

    try:
        # Run async workflow with an overall timeout
        # wait_for(...) returns a coroutine so this is safe to pass to asyncio.run
        coro = asyncio.wait_for(process_quiz_workflow(url, payload), timeout=BROWSER_TIMEOUT)
        result = asyncio.run(coro)
    except asyncio.TimeoutError:
        app.logger.exception("Timeout while processing quiz")
        return jsonify({"error": "processing timeout"}), 500
    except Exception as e:
        app.logger.exception("Processing failed")
        return jsonify({"error": f"processing failed: {str(e)}"}), 500

    return jsonify({
        "received": True,
        "email": email,
        "url": url,
        "result_meta": result.get("meta", {})
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Use 0.0.0.0 so Render/containers can bind correctly
    app.run(host="0.0.0.0", port=port)
