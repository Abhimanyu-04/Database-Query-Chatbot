# helpers/sql_runner.py

from sqlalchemy import text
from sqlalchemy.engine import Engine
from decimal import Decimal
import datetime
from typing import Any, Dict, List

def run_and_clean_sql(engine: Engine, query: str) -> List[Dict[str, Any]]:
    # Execute the raw SQL
    result = engine.execute(text(query))
    mappings = result.mappings().all()

    clean_rows: List[Dict[str, Any]] = []
    for row in mappings:
        clean_row: Dict[str, Any] = {}
        for col, val in row.items():
            if isinstance(val, Decimal):
                clean_row[col] = float(val)
            elif isinstance(val, datetime.datetime):
                clean_row[col] = val.isoformat()
            else:
                clean_row[col] = val
        clean_rows.append(clean_row)
    return clean_rows
