import subprocess, json, shlex
from pymongo import MongoClient
from typing import Any, Dict, List

# class MongoQueryTool:
#     def __init__(self, name: str, uri: str, db_name: str, collection_name: str):
#         self.name            = name
#         self.base_uri        = uri.rstrip("/")
#         self.db_name         = db_name
#         self.collection_name = collection_name
#         self.description     = f"Run mongosh find() on '{collection_name}' in DB '{db_name}'."

#         # metadata via pymongo
#         client = MongoClient(uri)
#         coll   = client[db_name][collection_name]
#         sample = coll.find_one({})
#         if not sample:
#             self.metadata = f"Collection '{collection_name}' is empty."
#         else:
#             fields = list(sample.keys())
#             self.metadata = f"Collection '{collection_name}' fields: {fields}"
        
#     def run(self, query_input: str) -> List[Dict[str,Any]]:
#         q = query_input.strip()
#         if not q.startswith("db."):
#             raise ValueError("Expected 'db.' style query")

#         js = f"const res={q}.toArray();print(JSON.stringify(res));"
#         conn = f"{self.base_uri}/{self.db_name}"
#         cmd = ["mongosh", conn, "--eval", js]
#         print("[MongoQueryTool] Running:", " ".join(shlex.quote(c) for c in cmd))

#         raw = subprocess.check_output(cmd, text=True).strip()
#         return json.loads(raw)

#     async def arun(self, qi: Any):
#         return self.run(qi)


class MongoQueryTool:
    def __init__(self, name: str, uri: str, db_name: str, collection_name: str):
        self.name            = name
        self.base_uri        = uri.rstrip("/")
        self.db_name         = db_name
        self.collection_name = collection_name
        self.description     = (
            f"Run mongosh find() on '{collection_name}' in DB '{db_name}'."
        )

        # metadata from pymongo
        client = MongoClient(uri)
        coll   = client[db_name][collection_name]
        sample = coll.find_one({})
        if not sample:
            self.metadata = f"Collection '{collection_name}' is empty."
        else:
            fields = list(sample.keys())
            self.metadata = f"Collection '{collection_name}' fields: {fields}"

    def run(self, query_input: str) -> List[Dict[str,Any]]:
        q = query_input.strip()
        if not q.startswith("db."):
            raise ValueError("Expected a shell-style Mongo query starting with 'db.'")

        
        js = (
            f"const res = {q}.toArray();\n"
            f"print( JSON.stringify(res) );"
        )

        
        conn = f"{self.base_uri}/{self.db_name}"
        cmd = ["mongosh", conn, "--eval", js]
        print("\n[MongoQueryTool] Running:", " ".join(shlex.quote(c) for c in cmd))

        
        raw = subprocess.check_output(cmd, text=True)

        
        raw = raw.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse mongosh JSON output:\n{raw}") from e

    async def arun(self, query_input: Any) -> List[Dict[str,Any]]:
        return self.run(query_input)

def make_mongo_tools(configs):
    tools, metadata = {}, {}
    for c in configs:
        tool = MongoQueryTool(
            name=c["name"],
            uri=c["uri"],
            db_name=c["db_name"],
            collection_name=c["collection_name"],
        )
        tools[c["name"]] = tool
        metadata[c["name"]] = tool.metadata
    return tools, metadata
