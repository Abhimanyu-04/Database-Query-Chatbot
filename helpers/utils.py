# helpers/utils.py

import json
from typing import Dict, List
from collections import defaultdict

def load_json(path: str) -> Dict:
    with open(path, "r") as f:
        return json.load(f)

def build_db_list_str(desc_cfg: List[Dict]) -> str:
    lines = []
    for db in desc_cfg:
        tbls = "\n".join(
            f"    • {t['name']}: {t['description']}"
            for t in db["tables"]
        )
        summary = db.get("summary")
        lines.append(f"- {db['name']} ({db['type']}): {summary}\n{tbls}")
    return "\n\n".join(lines)

def build_table_list_str(details_cfg: List[Dict], selected_db_names: List[str]) -> str:
    lines = []
    for db in details_cfg:
        if db["name"] not in selected_db_names:
            continue
        tbls = "\n".join(
            f"    • {t['name']}(table name): {t['description']}"
            for t in db["tables"]
        )
        lines.append(f"- {db['name']}(database name) tables:\n{tbls}")
    return "\n\n".join(lines)

def build_filtered_metadata_str(
    all_metadata: Dict[str,str],
    tables_by_db: Dict[str,List[str]],
    dialect_map: Dict[str,str]
) -> str:
    parts = []
    for db, schema in all_metadata.items():
        if db not in tables_by_db:
            continue
        if dialect_map[db] == "mongo":
            parts.append(f"{db} fields:\n{schema}")
        else:
            lines = schema.splitlines()
            keep = []
            i = 0
            while i < len(lines):
                ln = lines[i]
                if any(f"CREATE TABLE {tbl}" in ln for tbl in tables_by_db[db]):
                    block = [ln]; i += 1
                    while i < len(lines) and lines[i].strip() and not lines[i].startswith("CREATE TABLE"):
                        block.append(lines[i]); i += 1
                    keep.append("\n".join(block))
                else:
                    i += 1
            if keep:
                parts.append(f"{db} schema:\n\n" + "\n\n".join(keep))
    return "\n\n".join(parts)

def build_filtered_db_details_str(
    details_cfg: List[Dict],
    tables_by_db: Dict[str,List[str]]
) -> str:
    parts = []
    for db in details_cfg:
        name = db["name"]
        if name not in tables_by_db:
            continue
        header = f"{name} ({db['type']}): {db['description']}"
        tbls = [t for t in db["tables"] if t["name"] in tables_by_db[name]]
        lines = "\n".join(f"    • {t['name']}: {t['description']}" for t in tbls)
        parts.append(f"{header}\n{lines}")
    return "\n\n".join(parts)
