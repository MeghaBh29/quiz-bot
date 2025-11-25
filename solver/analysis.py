# solver/analysis.py
import re
import requests
import base64
from urllib.parse import urljoin
from solver.browser import fetch_rendered_page
from solver.parser_pdf import parse_pdf_sum_if_requested
from solver.parser_tabular import parse_csv_sum_if_requested, parse_excel_sum_if_requested

async def process_quiz_workflow(url: str, original_payload: dict):
    """
    Main workflow:
      1. fetch page via Playwright
      2. extract question text and look for download/file links
      3. if file exists, download and parse (pdf/csv/xlsx)
      4. build answer payload and POST to submit_url if present
    """
    page = await fetch_rendered_page(url)
    html = page["html"]
    text = page["text"]
    submit_url = find_submit_url(html) or find_submit_url(text)
    question = text.strip()[:2000]

    answer_obj = {"answer": None}
    # Simple heuristics: look for "download" or "sum" or "value" phrases
    if "download" in text.lower() or "download" in html.lower():
        file_link = find_file_link(html, url)
        if file_link:
            file_bytes = download_file(file_link)
            if file_bytes is not None:
                if file_link.lower().endswith(".pdf"):
                    total = parse_pdf_sum_if_requested(file_bytes)  # returns numeric or None
                    answer_obj["answer"] = total
                elif file_link.lower().endswith(".csv") or ".csv" in file_link.lower():
                    total = parse_csv_sum_if_requested(file_bytes)
                    answer_obj["answer"] = total
                elif file_link.lower().endswith(".xlsx") or file_link.lower().endswith(".xls"):
                    total = parse_excel_sum_if_requested(file_bytes)
                    answer_obj["answer"] = total
    # If nothing found, set raw text for manual inspection
    if answer_obj["answer"] is None:
        answer_obj["raw_text"] = question[:2000]

    meta = {"submit_url_found": bool(submit_url), "question_excerpt": question[:400]}
    if submit_url:
        # Build payload and submit
        payload = {
            "email": original_payload.get("email"),
            "secret": original_payload.get("secret"),
            "url": original_payload.get("url"),
            "answer": answer_obj.get("answer")
        }
        try:
            resp = requests.post(submit_url, json=payload, timeout=30)
            meta["submit_status_code"] = resp.status_code
            meta["submit_response_body"] = resp.text[:1000]
            # If server returned next url, consider chaining (not implemented: avoid loops)
            try:
                jr = resp.json()
                meta["submit_json"] = {k: jr.get(k) for k in ("correct","url","reason")}
            except Exception:
                pass
        except Exception as e:
            meta["submit_error"] = str(e)

    return {"answer": answer_obj, "meta": meta}

def find_submit_url(text_or_html: str):
    m = re.search(r'https?://[^\s"\'<>]+/submit[^\s"\'<>]*', text_or_html)
    return m.group(0) if m else None

def find_file_link(html: str, base_url: str):
    # Look for absolute or relative links to files (.pdf, .csv, .xlsx)
    m = re.search(r'href=["\'](https?://[^"\']+\.(?:pdf|csv|xlsx|xls))["\']', html, re.IGNORECASE)
    if m:
        return m.group(1)
    m2 = re.search(r'href=["\'](/[^"\']+\.(?:pdf|csv|xlsx|xls))["\']', html, re.IGNORECASE)
    if m2:
        return urljoin(base_url, m2.group(1))
    # also look for data URLs or direct mentions
    return None

def download_file(url: str):
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            return r.content
    except Exception:
        return None
    return None
