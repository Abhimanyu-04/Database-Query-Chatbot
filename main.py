import os
import json
import re
import logging
import cryptography
from logging.handlers import RotatingFileHandler
from collections import defaultdict
from typing import List, Dict, Any


from dotenv import load_dotenv
from helpers.utils import (
    load_json,
    build_table_list_str,
    build_filtered_metadata_str,
    build_filtered_db_details_str,
)
from tools.sql_tools     import make_sql_tools
from tools.mongo_tool    import make_mongo_tools
from agents.query_router     import make_query_router
from agents.verifier_agent   import make_verifier_agent
from agents.answer_generator import make_answer_agent
from agents.example_selector import get_similar_examples
from tools.execute_chained    import execute_chained
from langchain.schema import HumanMessage, AIMessage
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories import ChatMessageHistory

load_dotenv()

# logging
LOG_PATH = "logs/chatbot.log"
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logger = logging.getLogger("chatbot")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(LOG_PATH, maxBytes=2_000_000, backupCount=3)
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)

# agent creation
router    = make_query_router()
verifier  = make_verifier_agent()
answerer  = make_answer_agent()

# chat history
chat_history = ChatMessageHistory()
memory       = ConversationBufferMemory(
    chat_memory=chat_history,
    return_messages=True
)

chat_state = {
    "last_plan":     None,  
    "last_errors":   [],    
    "execute_ready": False,
}


def process_message(user_msg: str, selected_dbs: List[str]) -> Dict[str, Any]:

    logger.info(f"=== New message === USER: {user_msg} | DBS: {selected_dbs}")
    chat_history.add_message(HumanMessage(content=user_msg))

    db_cfg      = load_json("config/databases.json")
    desc_cfg    = load_json("config/db_desc.json")["databases"]
    details_cfg = load_json("config/db_details1.json")["databases"]

    pg_cfgs = [c for c in db_cfg["postgres_databases"] if c["name"] in selected_dbs]
    my_cfgs = [c for c in db_cfg["mysql_databases"]    if c["name"] in selected_dbs]
    mg_cfgs = [c for c in db_cfg["mongo_databases"]    if c["name"] in selected_dbs]

    logger.info(f"Filtered PG configs: {[c['name'] for c in pg_cfgs]}")
    logger.info(f"Filtered MY configs: {[c['name'] for c in my_cfgs]}")
    logger.info(f"Filtered MG configs: {[c['name'] for c in mg_cfgs]}")

    #tools+metadata
    sql_tools, sql_meta = make_sql_tools(pg_cfgs + my_cfgs)
    mg_tools,  mg_meta  = make_mongo_tools(mg_cfgs)
    all_tools    = {**sql_tools, **mg_tools}
    all_metadata = {**sql_meta,  **mg_meta}

    logger.info(f"All tools: {list(all_tools)}")
    logger.info(f"All metadata: {list(all_metadata)}")
    logger.info(f"All metadata items: {all_metadata.items()}")

    #Table selection
    table_list_str = build_table_list_str(details_cfg, selected_dbs)
    logger.info(f"table_list_str: {table_list_str}")
    from agents.table_selector import make_table_selector
    select_tables = make_table_selector(table_list_str)
    sel_tables    = select_tables(user_msg)
    logger.info(f"Selected tables: sel_tables={sel_tables}")
    tables_by_db  = defaultdict(list)
    for t in sel_tables:
        tables_by_db[t.db].append(t.table)

    logger.info(f"Selected tables: {[(t.db,t.table) for t in sel_tables]}")

    # filtered metadata & details
    dialect_map = {d["name"]: d["type"] for d in desc_cfg if d["name"] in tables_by_db}
    meta_str    = build_filtered_metadata_str(all_metadata, tables_by_db, dialect_map)
    details_str = build_filtered_db_details_str(details_cfg, tables_by_db)

    logger.info(f"Filtered metadata str:\n{meta_str}")
    logger.info(f"Filtered details str:\n{details_str}")

    # 5)examples
    examples = get_similar_examples(user_msg)
    logger.info(f"Selected examples: {examples}")

    # if execution
    if user_msg.strip().lower() == "go ahead" and not chat_state["last_errors"]:
        logger.info("User requested execution; running execute_chained…")
        logger.info(f"Last plan: {chat_state['last_plan']}")
        results = execute_chained(chat_state["last_plan"], all_tools)
        logger.info(f"Execution raw results: {results}")

        answer = answerer.invoke({
            "question":    user_msg,
            "all_results": results,
            "query":       chat_state["last_plan"]
        },memory=memory)["answer_text"]
        logger.info(f"Answerer output: {answer}")

        chat_history.add_message(AIMessage(content=answer))

        chat_state["execute_ready"] = False
        return {
            "plan":          chat_state["last_plan"],
            "explanations":  [],
            "errors":        [],
            "execute_ready": True,
            "raw_results":   results,
            "answer":        answer,
        }


    #Query creation
    router_out = router.invoke(
        {
            "input_question": user_msg,
            "all_metadata":   meta_str,
            "db_details":     details_str,
            "dialect_map":    json.dumps(dialect_map, indent=2),
            "examples":       examples,
            "errors":         json.dumps(chat_state["last_errors"], indent=2),
            "last_plan":      chat_state["last_plan"]
        },
        memory=memory
    )
    plan_json = router_out["query_plan_json"]
    chat_state["last_plan"] = plan_json
    logger.info(f"Router output plan_json:\n{plan_json}")

    summary = "Here’s the plan I drafted:\n" + plan_json
    chat_history.add_message(AIMessage(content=summary))

    # B2)verification
    ver_out = verifier.invoke(
        {
            "input_question":user_msg,
            "plan_json":   plan_json,
            "all_metadata":meta_str,
            "db_details":  details_str,
            "dialect_map": json.dumps(dialect_map, indent=2),
        },
        memory=memory
    )
    # logger.info(f"verifier output:\n{ver_out}")
    v     = json.loads(ver_out["verification"].replace("```json", "").replace("```", "").strip())
    expls = v.get("step_explanations", [])
    errs  = v.get("errors", [])
    chat_state["last_errors"]   = errs
    chat_state["execute_ready"] = (len(errs) == 0)

    logger.info(f"Verifier explanations: {expls}")
    logger.info(f"Verifier errors: {errs}")

    # if verifier found errors
    if errs:
        summary = "Here’s the plan I drafted (with issues):\n" + plan_json
        chat_history.add_message(AIMessage(content=summary))

    return {
        "plan":          plan_json,
        "explanations":  expls,
        "errors":        errs,
        "execute_ready": chat_state["execute_ready"],
    }


if __name__ == "__main__":
    demo = process_message(
        "What was power demand at 2023-04-09 00:00?",
        ["reserve_estimation", "power_demand", "dsm"]
    )
    print(json.dumps(demo, indent=2))
