import os, json
from langchain_community.vectorstores import FAISS
from langchain_core.example_selectors import SemanticSimilarityExampleSelector
from langchain_community.embeddings import HuggingFaceEmbeddings

from dotenv import load_dotenv
load_dotenv() 

# load your example‐pairs
with open("examples/sql_examples.json") as f:
    _examples = json.load(f)

_embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

_selector = SemanticSimilarityExampleSelector.from_examples(
    examples=_examples,
    embeddings=_embeddings,
    vectorstore_cls=FAISS,
    k=2,
    input_keys=["input"],
)

def get_similar_examples(question: str):
    return _selector.select_examples({"input": question})
