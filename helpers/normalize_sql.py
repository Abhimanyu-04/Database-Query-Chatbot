import re
import json
from ast import literal_eval
from decimal import Decimal
from typing import Any, Dict, List, Tuple, Union

def normalize_sql_output(
    raw: Union[str, List[Tuple[Any, ...]]]
) -> List[Dict[str, Any]]:
    if isinstance(raw, list):
        rows = []
        for tup in raw:
            if not isinstance(tup, tuple):
                tup = (tup,)
            row = {}
            for i, v in enumerate(tup):
                if isinstance(v, Decimal):
                    v = float(v)
                row[f"col_{i}"] = v
            rows.append(row)
        return rows

    s = str(raw).strip()

    
    if s.startswith("[") and ("{" in s or s.startswith('[{"')):
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list) and all(isinstance(x, dict) for x in parsed):
                return parsed
        except json.JSONDecodeError:
            pass

    
    start = s.find("[")
    end   = s.rfind("]") + 1
    if start < 0 or end <= start:
        raise ValueError(f"Cannot find list in SQL output:\n{s}")
    snippet = s[start:end]

    
    def _dec_to_num(m):
        return m.group(1)
    snippet = re.sub(
        r"Decimal(?:128)?\(\s*['\"](-?[0-9]+(?:\.[0-9]+)?)['\"]\s*\)",
        _dec_to_num,
        snippet
    )

    
    def _dt_to_str(m):
        parts = [int(p) for p in m.groups() if p is not None]
        # year,month,day,hour,minute,(second)
        y, mo, d, h, mi, sec = (*parts, 0)[:6]
        iso = f"{y:04d}-{mo:02d}-{d:02d}T{h:02d}:{mi:02d}:{sec:02d}"
        return f"'{iso}'"
    snippet = re.sub(
        r"datetime\.datetime\(\s*([0-9]+),\s*([0-9]+),\s*([0-9]+),\s*([0-9]+),\s*([0-9]+)(?:,\s*([0-9]+))?\s*\)",
        _dt_to_str,
        snippet
    )

    
    snippet = re.sub(
        r"([{,])\s*([A-Za-z_][A-Za-z0-9_]*)\s*:",
        r'\1"\2":',
        snippet
    )

    
    try:
        tuples = literal_eval(snippet)
    except Exception as e:
        raise ValueError(f"Failed parsing cleaned SQL output:\n{snippet}\nError: {e}")

    
    rows = []
    for tup in tuples:
        if not isinstance(tup, tuple):
            tup = (tup,)
        row = {}
        for i, v in enumerate(tup):
            row[f"col_{i}"] = v
        rows.append(row)

    return rows




# # helpers/normalize_sql.py

# import re
# import json
# from ast import literal_eval
# from decimal import Decimal
# import datetime
# from typing import Any, Dict, List, Tuple, Union, Optional

# def normalize_sql_output(
#     raw: Union[str, List[Tuple[Any, ...]]],
#     col_names: Optional[List[str]] = None
# ) -> List[Dict[str, Any]]:
#     """
#     Normalize raw SQL output (either a list of tuples or a repr‐string)
#     into a list of dicts.  If col_names is given, use those instead of
#     col_0, col_1, … keys.

#     Converts:
#       - Decimal(...) → float
#       - datetime.datetime(...) → ISO8601 string ending in Z
#     """
#     # 1) If it's already a Python list of tuples
#     if isinstance(raw, list):
#         rows: List[Dict[str, Any]] = []
#         for tup in raw:
#             if not isinstance(tup, tuple):
#                 tup = (tup,)
#             row: Dict[str, Any] = {}
#             for i, v in enumerate(tup):
#                 # Decimal → float
#                 if isinstance(v, Decimal):
#                     v = float(v)
#                 # datetime → ISO string
#                 if isinstance(v, datetime.datetime):
#                     # ensure we include seconds and Z
#                     v = v.replace(tzinfo=None).isoformat() + "Z"
#                 # choose column name
#                 key = col_names[i] if (col_names and i < len(col_names)) else f"col_{i}"
#                 row[key] = v
#             rows.append(row)
#         return rows

#     # 2) Otherwise it's a string repr; pull off the [ … ] slice
#     s = str(raw).strip()
#     # If it already looks like a JSON list of dicts, try JSON first
#     if s.startswith("[") and ("{" in s):
#         try:
#             parsed = json.loads(s)
#             if isinstance(parsed, list) and all(isinstance(x, dict) for x in parsed):
#                 return parsed  # already good
#         except json.JSONDecodeError:
#             pass

#     # Find the Python‐list substring
#     start = s.find("[")
#     end   = s.rfind("]") + 1
#     if start < 0 or end <= start:
#         raise ValueError(f"Cannot find list in SQL output:\n{s}")
#     snippet = s[start:end]

#     # 3) Replace Decimal → bare number
#     snippet = re.sub(
#         r"Decimal(?:128)?\(\s*['\"](-?[0-9]+(?:\.[0-9]+)?)['\"]\s*\)",
#         r"\1",
#         snippet
#     )

#     # 4) Replace datetime.datetime(...) → ISO8601 string literal
#     def _dt_to_iso(m: re.Match) -> str:
#         # groups: year, month, day, hour, minute, [second]
#         parts = [int(g) for g in m.groups() if g is not None]
#         y, mo, d, h, mi, sec = (*parts, 0)[:6]
#         iso = f"{y:04d}-{mo:02d}-{d:02d}T{h:02d}:{mi:02d}:{sec:02d}"
#         return f"'{iso}Z'"
#     snippet = re.sub(
#         r"datetime\.datetime\(\s*([0-9]+),\s*([0-9]+),\s*([0-9]+),\s*([0-9]+),\s*([0-9]+)(?:,\s*([0-9]+))?\s*\)",
#         _dt_to_iso,
#         snippet
#     )

#     # 5) Ensure keys are quoted so literal_eval sees valid dicts
#     snippet = re.sub(
#         r"([{,])\s*([A-Za-z_][A-Za-z0-9_]*)\s*:",
#         r'\1"\2":',
#         snippet
#     )

#     # 6) literal_eval into Python objects
#     try:
#         tuples = literal_eval(snippet)
#     except Exception as e:
#         raise ValueError(f"Failed parsing cleaned SQL output:\n{snippet}\nError: {e}")

#     # 7) Convert list of tuples into list of dicts
#     rows = []
#     for tup in tuples:
#         if not isinstance(tup, tuple):
#             tup = (tup,)
#         row: Dict[str, Any] = {}
#         for i, v in enumerate(tup):
#             # no more Decimal or datetime at this point, but just in case:
#             if isinstance(v, Decimal):
#                 v = float(v)
#             if isinstance(v, datetime.datetime):
#                 v = v.replace(tzinfo=None).isoformat() + "Z"
#             key = col_names[i] if (col_names and i < len(col_names)) else f"col_{i}"
#             row[key] = v
#         rows.append(row)

#     return rows
