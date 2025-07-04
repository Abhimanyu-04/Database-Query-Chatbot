import os
from pydantic import BaseModel, Field
from typing import List
from langchain.chains.openai_tools import create_extraction_chain_pydantic
from langchain_openai import ChatOpenAI

from dotenv import load_dotenv
load_dotenv() 

class SelectedDB(BaseModel):
    name: str = Field(description="Name of a database relevant to the question")

def make_db_selector(db_list_str: str):
    prompt = f"""
    You have these data stores and their tables:
    {db_list_str}
    Which database(s) would be relevant to answer the user's question?
    Return only a JSON list of database names. Do not output any other text.
    """
    chain = create_extraction_chain_pydantic(
        SelectedDB,
        llm=ChatOpenAI(
            temperature=0,
            model="llama3-8b-8192",
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY")
        ),
        system_message=prompt
    )
    def select_databases(question: str) -> List[str]:
        models = chain.invoke({"input": question})
        return [m.name for m in models]
    return select_databases
