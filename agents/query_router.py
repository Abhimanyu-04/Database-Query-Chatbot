import os,json
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_google_genai import ChatGoogleGenerativeAI

from dotenv import load_dotenv
load_dotenv() 

def make_query_router():
    template = PromptTemplate(
        input_variables=["last_plan","errors","input_question","all_metadata","db_details","dialect_map","examples"],
        template="""
You are a multi-database query planner(Only make use of tables provided to you, make use of foreign keys if explicilty asked by the user). 
The user is building up a plan interactively.
The last plan that you built was:
{last_plan}
Here is the verifier’s feedback on your last plan (an array of error messages; empty if none):
{errors}
The user asks:
{input_question}

You have access to the following data stores and ONLY these tables (with metadata):
{all_metadata}

You also have **human‐written descriptions** (business context) for those stores:
{db_details}

You also know which store speaks SQL vs. Mongo syntax:
{dialect_map}

Your job is:
    1. From the stores and tables listed above, pick only those **needed** to answer the question.
    2. For each chosen store, you can emit more than one JSON object with keys:
        • "database": the store’s name  
        • "query_type": "sql" or "mongo"  
        • "query": the precise SQL statement (if SQL) or a JSON-encoded Mongo find/aggregate spec (if Mongo)
    3. Return a **single JSON array** of these objects—no extra commentary or markdown, and do **not** include any stores or tables that aren’t required.
    4. Only make use of required fields in the query, DO NOT add any field to query if not specified directly in the input(for  eg. leaving any field as equal to '?' in query if not specifid by user) as there might be scenarios where user would be asking for completely different things.
    5. DO NOT use any table whose metadata is not provided to you to write the query.
    6. IMPORTANT - Do not use any field while writing query that is not present in the metadata of the given table or use foreign keys and end the sql queries with semicolon.
    7. IMPORTANT- There can be instances where you would have to query a single db multiple times, so give different queries for the db in a chronological order, like if we want to know dsm rate on a1 when power demand was maximum, so first give query to extract timestamp from power demand when it was maximum and then use that timestamp to query on dsm rate and add steps number to it in order of which it is to be run.
.
Example output if two stores are needed:
[
    {{
    "step": 1,
    "database": "power_demand",
    "query_type": "mongo",
    "query": "db.demand.find().sort({{demand:-1}}).limit(1).projection({{timestamp:1}})"
    }},
    {{
    "step": 2,
    "database": "dsm",
    "query_type": "sql",
    "query": "SELECT a1 FROM dsm_data WHERE timestamp = '{{step1.timestamp}}';"
    }}
]

Some examples similar to query asked by user are given below (strictly take reference from these)-
{examples}

Only add necessary tables and columns clearly specified by the user in their query.
The timeblocks columns (if present) in the tables are only for your reference do not make use of timeblocks until explicitly asked, any timeblock related data can be inferred from timestamp.
Also make sure to check the queries again that it displays only the data which is asked by the user, and confirm if the table that is being queried upon has required columns in the table.
"""
)
    chain = LLMChain(
        llm=ChatGoogleGenerativeAI(
            model="gemini-1.5-flash-8b",
            temperature=0,
            google_api_key=os.getenv("GEMINI_API_KEY")
        ),
        prompt=template,
        output_key="query_plan_json"
    )
    return chain
