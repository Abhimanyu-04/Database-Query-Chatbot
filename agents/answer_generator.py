import os
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI

from dotenv import load_dotenv
load_dotenv() 

def make_answer_agent():
    prompt = PromptTemplate(
        input_variables=["question","all_results","query"],
        template="""
        You are a db results to natural language assistant.  A user asked:

        {question}

        The queries generated were:

        {query}

        You ran them and got:

        {all_results}

        Please write a single, clear, natural-language answer to the user’s question,
        explaining what each result means.  Do not include any SQL or Mongo syntax—
        just the English explanation.
        Don't answer the question directly based on the SQL result, but rather rephrase the answer in a more natural way which will be more human understandable, 
        but also do not make any approximations while displaying the result unless the user asks to do so, exactly display the result as it is.
        Also do not give any units to the answer if not known.
        """
    )
    return LLMChain(
        llm=ChatOpenAI(
            temperature=0,
            model="llama3-8b-8192",
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY")
        ),
        prompt=prompt,
        output_key="answer_text"
    )
