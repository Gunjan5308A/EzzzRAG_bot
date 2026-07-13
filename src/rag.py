import os
import chromadb
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from config import CHROMA_API_KEY
from src.model import default_embeddings, default_llm, create_llm

IS_TESTING = True 

if IS_TESTING:
    chroma_client = chromadb.EphemeralClient()
else:
    chroma_client = chromadb.CloudClient(
        api_key=os.getenv("CHROMA_API_KEY"),
        tenant="default",
        database="default"
    )

vector_store = Chroma(
    client=chroma_client,
    collection_name="serverless_rag",
    embedding_function=default_embeddings,
)

template = "Answer the question based only on the context:\nContext:\n{context}\n\nQuestion: {question}"
prompt = ChatPromptTemplate.from_template(template)

def format_docs(docs):
    return "\n".join(doc.page_content for doc in docs)

def add_chunks(chunks: list[str],  bot_id: int):
    metadata = [{"bot_id": bot_id} for chunk in chunks]
    vector_store.add_texts(texts=chunks, metadatas=metadata)

def ask_question(question: str, bot_id) -> str:
    retriever = vector_store.as_retriever(search_kwargs={"k": 3, "filter": {"bot_id": bot_id}})
    llm = create_llm(temperature=0)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return rag_chain.invoke(question)
