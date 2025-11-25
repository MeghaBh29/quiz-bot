# solver/parser_pdf.py
import io
import pdfplumber
import pandas as pd

def parse_pdf_sum_if_requested(pdf_bytes: bytes, column_name="value", page_number=2):
    """
    Open PDF bytes, try to extract tables from the given page (1-indexed).
    If a table contains a column named like `column_name`, sum its numeric values.
    Returns float total or None if not found.
    """
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        total = 0.0
        found_any = False

        # Determine pages to inspect
        if len(pdf.pages) >= page_number:
            pages_to_check = [page_number - 1]
        else:
            pages_to_check = range(len(pdf.pages))

        for p_idx in pages_to_check:
            page = pdf.pages[p_idx]
            try:
                tables = page.extract_tables()
            except Exception:
                tables = []
            for table in tables:
                # table: list of rows; first row often header
                if not table or len(table) < 2:
                    continue
                try:
                    df = pd.DataFrame(table[1:], columns=table[0])
                except Exception:
                    # fallback: build df without header if mismatch
                    df = pd.DataFrame(table)
                cols_lower = [str(c).strip().lower() for c in df.columns]
                if column_name.lower() in cols_lower:
                    col = df.columns[cols_lower.index(column_name.lower())]
                    series = pd.to_numeric(df[col].astype(str).str.replace('[^0-9.-]', '', regex=True), errors='coerce')
                    total += series.sum(skipna=True)
                    found_any = True

        if not found_any:
            return None
        return float(total)
