import os
from pydantic import BaseModel, Field
from typing import List
from langchain.chains.openai_tools import create_extraction_chain_pydantic
from langchain_openai import ChatOpenAI

from dotenv import load_dotenv
load_dotenv() 

class SelectedTable(BaseModel):
    db: str = Field(description="Database name")
    table: str = Field(description="Table name in that database")

def make_table_selector(table_list_str: str):
    prompt = f"""
    You have these tables in the selected databases:

    {table_list_str}

    Which specific tables would you need to answer the user’s question?
    Return a JSON list of objects like {{{{ "db": "<database_name>", "table": "<table_name>" }}}}.
    Do NOT return any other keys or extra text.
    """
    chain = create_extraction_chain_pydantic(
        SelectedTable,
        llm=ChatOpenAI(temperature=0, model="llama3-8b-8192",
                       base_url="https://api.groq.com/openai/v1",
                       api_key=os.getenv("GROQ_API_KEY")),
        system_message=prompt
    )
    def select_tables(question: str) -> List[SelectedTable]:
        return chain.invoke({"input": question})
    return select_tables
