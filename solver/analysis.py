# solver/analysis.py
import re
import time
import requests
from urllib.parse import urljoin
from solver.browser import fetch_rendered_page
from solver.parser_pdf import parse_pdf_sum_if_requested
from solver.parser_tabular import parse_csv_sum_if_requested, parse_excel_sum_if_requested

async def process_quiz_workflow(start_url: str, original_payload: dict):
    """
    End-to-end workflow for one quiz URL:
    - fetch rendered page using Playwright
    - extract question and look for file links and submit URL
    - download and parse files (PDF/CSV/XLSX) using parser helpers
    - submit answer to detected submit_url if present
    Returns dict with answer and meta info.
    """
    start_time = time.time()
    max_total_seconds = 180  # keep under 3 minutes; workflow should be faster
    page = await fetch_rendered_page(start_url)
    html = page.get("html", "")
    text = page.get("text", "")

    submit_url = find_submit_url(html) or find_submit_url(text)
    question_excerpt = text.strip()[:2000]

    answer_obj = {"answer": None}

    # Heuristic: if page mentions "download" or contains file links, try to fetch and parse
    file_link = find_file_link(html, start_url)
    if file_link:
        file_bytes = download_file(file_link)
        if file_bytes:
            low = file_link.lower()
            if low.endswith(".pdf"):
                total = parse_pdf_sum_if_requested(file_bytes)
                answer_obj["answer"] = total
            elif low.endswith(".csv") or ".csv" in low:
                total = parse_csv_sum_if_requested(file_bytes)
                answer_obj["answer"] = total
            elif low.endswith(".xlsx") or low.endswith(".xls"):
                total = parse_excel_sum_if_requested(file_bytes)
                answer_obj["answer"] = total

    # If no file-driven answer found, attempt to parse inline instructions for simple numeric answers (optional)
    if answer_obj["answer"] is None:
        # Example: look for explicit "answer: 12345" patterns (very naive)
        m = re.search(r'answer[:=]\s*([0-9\.\-]+)', text, re.IGNORECASE)
        if m:
            try:
                answer_obj["answer"] = float(m.group(1))
            except Exception:
                answer_obj["answer"] = m.group(1)

    # Prepare meta and, if submit_url found, submit the answer
    meta = {"submit_url_found": bool(submit_url), "question_excerpt": question_excerpt[:400]}
    if submit_url:
        payload = {
            "email": original_payload.get("email"),
            "secret": original_payload.get("secret"),
            "url": original_payload.get("url"),
            "answer": answer_obj.get("answer")
        }
        try:
            resp = requests.post(submit_url, json=payload, timeout=30)
            meta["submit_status_code"] = resp.status_code
            meta["submit_response_text"] = resp.text[:1000]
            # If submit returned json with next url, include it
            try:
                jr = resp.json()
                meta["submit_json"] = {k: jr.get(k) for k in ("correct", "url", "reason")}
            except Exception:
                pass
        except Exception as e:
            meta["submit_error"] = str(e)

    # Optionally: if submit returned a new URL and time remains, you could follow it here.
    # (Chaining logic is not implemented to avoid loops; you can extend it.)
    meta["elapsed_seconds"] = time.time() - start_time
    return {"answer": answer_obj, "meta": meta}

def find_submit_url(text_or_html: str):
    m = re.search(r'https?://[^\s"\'<>]+/submit[^\s"\'<>]*', text_or_html)
    return m.group(0) if m else None

def find_file_link(html: str, base_url: str):
    # Absolute links
    m = re.search(r'href=["\'](https?://[^"\']+\.(?:pdf|csv|xlsx|xls))["\']', html, re.IGNORECASE)
    if m:
        return m.group(1)
    # Relative links
    m2 = re.search(r'href=["\'](/[^"\']+\.(?:pdf|csv|xlsx|xls))["\']', html, re.IGNORECASE)
    if m2:
        return urljoin(base_url, m2.group(1))
    # Look for direct textual mention of a link
    m3 = re.search(r'(https?://[^\s"\'<>]+(?:pdf|csv|xlsx|xls))', html, re.IGNORECASE)
    if m3:
        return m3.group(1)
    return None

def download_file(url: str):
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            return r.content
        return None
    except Exception:
        return None
