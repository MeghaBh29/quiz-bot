# app.py
import os
import asyncio
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from solver.analysis import process_quiz_workflow

# Load local .env during dev (don't commit .env)
load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

EXPECTED_SECRET = os.environ.get("QUIZ_SECRET", "s3cr3t-for-quiz-XYZ")
BROWSER_TIMEOUT = int(os.environ.get("BROWSER_TIMEOUT", "120"))

@app.route("/quiz_endpoint", methods=["POST"])
def quiz_endpoint():
    # Validate JSON
    if not request.is_json:
        return jsonify({"error": "invalid json"}), 400
    payload = request.get_json()
    email = payload.get("email")
    secret = payload.get("secret")
    url = payload.get("url")
    if not email or not secret or not url:
        return jsonify({"error": "missing fields"}), 400
    if secret != EXPECTED_SECRET:
        return jsonify({"error": "invalid secret"}), 403

    try:
        # Run async workflow with an overall timeout
        result = asyncio.run(asyncio.wait_for(process_quiz_workflow(url, payload), timeout=BROWSER_TIMEOUT))
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
    app.run(host="0.0.0.0", port=port)
