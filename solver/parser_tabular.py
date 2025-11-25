# solver/parser_tabular.py
import io
import pandas as pd

def parse_csv_sum_if_requested(csv_bytes: bytes, column_name="value"):
    """
    Parse CSV bytes and sum numeric values in the column named `column_name` (case-insensitive).
    Returns float or None.
    """
    try:
        df = pd.read_csv(io.BytesIO(csv_bytes))
    except Exception:
        return None

    col_map = {str(c).strip().lower(): c for c in df.columns}
    if column_name.lower() not in col_map:
        return None
    real_col = col_map[column_name.lower()]
    series = pd.to_numeric(df[real_col].astype(str).str.replace('[^0-9.-]', '', regex=True), errors='coerce')
    return float(series.sum(skipna=True))

def parse_excel_sum_if_requested(xlsx_bytes: bytes, column_name="value", sheet=None):
    """
    Parse Excel bytes and sum a named column. `sheet` can be None (defaults to first sheet).
    Returns float or None.
    """
    try:
        df = pd.read_excel(io.BytesIO(xlsx_bytes), sheet_name=sheet)
    except Exception:
        return None

    col_map = {str(c).strip().lower(): c for c in df.columns}
    if column_name.lower() not in col_map:
        return None
    real_col = col_map[column_name.lower()]
    series = pd.to_numeric(df[real_col].astype(str).str.replace('[^0-9.-]', '', regex=True), errors='coerce')
    return float(series.sum(skipna=True))
