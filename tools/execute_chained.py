# for testing
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import json
import re
from typing import Any, Dict, List
from helpers.normalize_sql import normalize_sql_output
from sqlalchemy import text


# for testing
from tools.sql_tools     import make_sql_tools
from tools.mongo_tool    import make_mongo_tools
from helpers.utils import load_json


def execute_chained(
    plan_json: str,
    all_tools: Dict[str, Any],
) -> Dict[str, List[Dict[str, Any]]]:
    

    # extracting json array
    start = plan_json.find("[")
    end   = plan_json.rfind("]") + 1
    steps = json.loads(plan_json[start:end])

    step_results: Dict[int, List[Dict[str, Any]]] = {}
    final: Dict[str, List[Dict[str, Any]]] = {}

    #execution
    for step in sorted(steps, key=lambda x: x["step"]):
        n     = step["step"]
        db    = step["database"]
        typ   = step["query_type"]
        raw_q = step["query"]

        #for {stepM.field} placeholders
        def _repl(m):
            key = m.group(1)            
            sn, fld = key.split(".", 1) 
            prev = int(sn.replace("step", "")) 
            return str(step_results[prev][0][fld])

        q = re.sub(r"\{(step\d+\.\w+)\}", _repl, raw_q)

        tool = all_tools[db]
        if typ == "sql":
            # raw  = tool.db.run(q)
            # rows = normalize_sql_output(raw)
            sql_tool = all_tools[db]
            engine   = sql_tool.db._engine  # SQLDatabase stores its Engine here
            with engine.connect() as conn:
                result = conn.execute(text(q))
                # .mappings().all() gives List[dict[column_name→value]]
                rows = result.mappings().all()
        else:  
            rows = tool.run(q)

        step_results[n]      = rows
        final[f"step{n}"]    = rows
        print(final)    

    return final

if __name__ == "__main__":
    test_plan_json = """
    ```json
    [
    {
        "step": 1,
        "database": "reserve_estimation",
        "query_type": "sql",
        "query": "SELECT timestamp FROM estimated_reserve WHERE sr_down IS NOT NULL ORDER BY sr_down ASC LIMIT 1;"
    },
    {
        "step": 2,
        "database": "demand_data",
        "query_type": "mongo",
        "query": "db.demand.find({timestamp: ISODate('{step1.timestamp}')}, {_id: 0, demand: 1, timestamp: 1})"
    }
    ]
    ```
    """

    db_cfg      = load_json("config/databases.json")
    pg_cfgs = [c for c in db_cfg["postgres_databases"]]
    my_cfgs = [c for c in db_cfg["mysql_databases"]   ]
    mg_cfgs = [c for c in db_cfg["mongo_databases"]   ]
    sql_tools, sql_meta = make_sql_tools(pg_cfgs + my_cfgs)
    mg_tools,  mg_meta  = make_mongo_tools(mg_cfgs)
    all_tools    = {**sql_tools, **mg_tools}
    all_metadata = {**sql_meta,  **mg_meta}

    print(execute_chained(test_plan_json, all_tools))

