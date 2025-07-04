from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
import cryptography

def make_sql_tools(configs):
    """
    Given a list of {name,dialect,uri}, return dict(name→tool) and dict(name→schema_str).
    """
    tools, metadata = {}, {}
    for cfg in configs:
        sql_db = SQLDatabase.from_uri(cfg["uri"])
        tool = QuerySQLDataBaseTool(
            db=sql_db,
            name=cfg["name"],
            description=f"Run SQL queries against '{cfg['name']}'."
        )
        tools[cfg["name"]] = tool
        metadata[cfg["name"]] = sql_db.get_table_info()
    return tools, metadata
