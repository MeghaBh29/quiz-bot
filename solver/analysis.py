# solver/analysis.py
import os
import re
import time
import json
import requests
from urllib.parse import urljoin
from solver.browser import fetch_rendered_page
from solver.parser_pdf import parse_pdf_sum_if_requested
from solver.parser_tabular import parse_csv_sum_if_requested, parse_excel_sum_if_requested
# --- add these helper functions to solver/analysis.py ---

import re
import requests
from urllib.parse import urljoin

def find_submit_url(text_or_html: str):
    """
    Look for a submit endpoint in the HTML/text.
    Common patterns: https://.../submit or /submit endpoints.
    Returns full URL string or None.
    """
    if not text_or_html:
        return None
    # try common absolute submit endpoints first
    m = re.search(r'https?://[^\s"\'<>]*?/submit[^\s"\'<>]*', text_or_html, re.IGNORECASE)
    if m:
        return m.group(0)
    # try relative /submit paths inside href attributes or text
    m = re.search(r'href=["\'](/[^"\']*?/submit[^"\']*)["\']', text_or_html, re.IGNORECASE)
    if m:
        return m.group(1)
    # fallback: any path that ends with /submit
    m = re.search(r'(["\'])(/[^"\']*?/submit[^"\']*)\1', text_or_html, re.IGNORECASE)
    if m:
        return m.group(2)
    return None

def find_file_link(html: str, base_url: str):
    """
    Heuristic to find a downloadable file (pdf/csv/xlsx) link in HTML/text.
    Returns absolute URL or None.
    """
    if not html:
        return None

    # 1) absolute hrefs
    m = re.search(r'href=["\'](https?://[^"\']+\.(?:pdf|csv|xlsx|xls))["\']', html, re.IGNORECASE)
    if m:
        return m.group(1)

    # 2) relative hrefs (convert to absolute)
    m = re.search(r'href=["\'](/[^"\']+\.(?:pdf|csv|xlsx|xls))["\']', html, re.IGNORECASE)
    if m and base_url:
        return urljoin(base_url, m.group(1))

    # 3) raw URLs in text
    m = re.search(r'(https?://[^\s"\'<>]+?\.(?:pdf|csv|xlsx|xls))', html, re.IGNORECASE)
    if m:
        return m.group(1)

    # 4) lazy-loaded links (data-href, data-src)
    m = re.search(r'(data-(?:href|src)=["\'](https?://[^\s"\'<>]+?\.(?:pdf|csv|xlsx|xls))["\'])', html, re.IGNORECASE)
    if m:
        return re.search(r'https?://[^\s"\'<>]+?\.(?:pdf|csv|xlsx|xls)', m[0], re.IGNORECASE).group(0)

    return None

def download_file(url: str, timeout: int = 30):
    """
    Download a file (bytes) with a timeout. Returns bytes or None.
    """
    if not url:
        return None
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            return r.content
    except Exception:
        return None
    return None

# --- end helper functions ---

# Use env defaults if present
MAX_TOTAL_SECONDS = int(os.environ.get("BROWSER_TIMEOUT", "180"))
MAX_STEPS = int(os.environ.get("MAX_STEPS", "6"))
OUTGOING_SIZE_LIMIT = int(os.environ.get("OUTGOING_JSON_LIMIT_BYTES", 1_000_000))  # 1MB

async def process_quiz_workflow(start_url: str, original_payload: dict):
    start_time = time.time()
    elapsed = 0.0
    current_url = start_url
    steps = 0
    full_meta = {"steps": []}
    last_submit_response = None

    while current_url and (time.time() - start_time) < MAX_TOTAL_SECONDS and steps < MAX_STEPS:
        steps += 1
        step_start = time.time()
        step_meta = {"url": current_url, "step": steps}

        # Fetch rendered page
        try:
            page = await fetch_rendered_page(current_url)
            html = page.get("html", "") or ""
            text = page.get("text", "") or html
            step_meta["fetched"] = True
        except Exception as e:
            step_meta["fetched"] = False
            step_meta["fetch_error"] = str(e)
            full_meta["steps"].append(step_meta)
            break

        # Find submit url and any file link
        submit_url = find_submit_url(html) or find_submit_url(text)
        file_link = find_file_link(html, current_url)
        step_meta.update({"submit_url": submit_url, "file_link": file_link})

        # Try to compute an answer
        answer_val = None

        # 1) If file link present, try to download & parse
        if file_link:
            try:
                file_bytes = download_file(file_link)
                if file_bytes:
                    low = file_link.lower()
                    if low.endswith(".pdf"):
                        answer_val = parse_pdf_sum_if_requested(file_bytes)
                    elif ".csv" in low:
                        answer_val = parse_csv_sum_if_requested(file_bytes)
                    elif low.endswith(".xlsx") or low.endswith(".xls"):
                        answer_val = parse_excel_sum_if_requested(file_bytes)
                step_meta["file_parsed"] = answer_val is not None
            except Exception as e:
                step_meta["file_error"] = str(e)

        # 2) Inline numeric pattern fallback
        if answer_val is None:
            m = re.search(r'answer\s*[:=]\s*["\']?([0-9\.\-]+)["\']?', text, re.IGNORECASE)
            if m:
                try:
                    answer_val = float(m.group(1))
                except:
                    answer_val = m.group(1)

        # 3) Inline quoted string pattern fallback
        if answer_val is None:
            m2 = re.search(r'answer\s*[:=]\s*["\'](.{1,200}?)["\']', text, re.IGNORECASE)
            if m2:
                answer_val = m2.group(1).strip()

        # 4) final safe fallback required by demo — non-null string
        if answer_val is None:
            answer_val = "no-answer-found"

        step_meta["answer_candidate"] = answer_val

        # Submit if submit_url exists
        submit_response_json = None
        if submit_url:
            payload = {
                "email": original_payload.get("email"),
                "secret": original_payload.get("secret"),
                "url": current_url,
                "answer": answer_val
            }

            # Enforce outgoing JSON size limit
            try:
                payload_json = json.dumps(payload, default=str)
            except Exception:
                payload_json = json.dumps({
                    "email": payload.get("email"),
                    "secret": "***REDACTED***",
                    "url": payload.get("url"),
                    "answer": str(payload.get("answer"))
                })

            if len(payload_json.encode("utf-8")) > OUTGOING_SIZE_LIMIT:
                step_meta["submit_error"] = "payload_too_large"
            else:
                try:
                    resp = requests.post(submit_url, json=payload, timeout=30)
                    step_meta["submit_status_code"] = resp.status_code
                    step_meta["submit_response_text"] = resp.text[:2000]
                    try:
                        submit_response_json = resp.json()
                        step_meta["submit_json"] = {k: submit_response_json.get(k) for k in ("correct", "url", "reason")}
                    except Exception:
                        submit_response_json = None
                except Exception as e:
                    step_meta["submit_error"] = str(e)

        full_meta["steps"].append(step_meta)
        last_submit_response = submit_response_json

        # Determine next url from submit response
        next_url = None
        if submit_response_json and isinstance(submit_response_json, dict):
            next_url = submit_response_json.get("url")

        # update current_url for next loop or stop
        if not next_url:
            break
        current_url = next_url

        # enforce time budget check
        elapsed = time.time() - start_time
        if elapsed >= MAX_TOTAL_SECONDS:
            break

    full_meta["elapsed_seconds"] = time.time() - start_time
    return {"answer": {"last": answer_val}, "meta": full_meta}
