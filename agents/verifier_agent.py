import os, json
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

def make_verifier_agent():
    prompt = PromptTemplate(
        input_variables=[
            "plan_json",
            "all_metadata",
            "db_details",
            "dialect_map"
        ],
        template="""
        You are a *query‐plan verifier*.  You have the conversation history in memory.

        Here is the proposed plan as JSON (an array of steps):
        {plan_json}

        Metadata for each store (table → columns):
        {all_metadata}

        Business‑level descriptions of each table:
        {db_details}

        Which stores use SQL vs. Mongo:
        {dialect_map}

        Your job is to produce **only** a JSON object with two keys:

        1. **step_explanations**  
          – a list of one‑sentence explanations of *exactly* what each step’s query does (no reference to the user’s question).

        2. **errors**  
          – a list of zero or more objects describing any problems. Each error object must have:
            - `"step"`: the step number  
            - `"message"`: a brief description of the issue  
            - `"suggested_fix"`: a placeholder‑style fix, e.g. `"Use field '<field_name>' instead"`

        Perform these checks:

        A) **Correctness** – does the query actually fetch the intended column(s)?  
        B) **Syntax** – is the SQL or Mongo syntax valid?  
        C) **Metadata consistency** – do all referenced tables & columns exist in the metadata?  

        **Important:**  
        - Treat any placeholder reference of the form `stepN.<field_name>` (e.g. `step1.timestamp`) as intentional—do *not* flag these as errors.  
        - Use placeholders (`<field_name>`, `<table_name>`, `<keyword>`) in your suggestions instead of real values.  
        - Do *not* inject advice about semicolons unless an actual syntax error in a concrete query.

        Return JSON *only* in this exact shape:\
        {{
          "step_explanations": [
            "Step 1 queries the 'demand' collection for the highest demand timestamp.",
            "Step 2 selects a1 from dsm_data for the given timestamp."
          ],
          "errors": [
            {{
              "step": 2,
              "message": "missing field '<field_name>' in table '<table_name>'",
              "suggested_fix": "Use field '<correct_field_name>' instead"
            }},
            {{
              "step": 3,
              "message": "syntax error near '<keyword>'",
              "suggested_fix": "Correct the keyword '<keyword>'"
            }}
          ]
        }}

        If there are no issues, "errors" must be an empty array.
        """
)


    return LLMChain(
        llm=ChatGoogleGenerativeAI(
            model="gemini-1.5-flash-8b",
            temperature=0,
            google_api_key=os.getenv("GEMINI_API_KEY")
        ),
        prompt=prompt,
        output_key="verification"
    )
