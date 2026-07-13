import os
import chromadb
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from config import OPENAI_API_KEY, CHROMA_API_KEY, OpenAI_base_URL, EMBEDDING_MODEL


os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

chroma_client = chromadb.CloudClient(
    api_key=CHROMA_API_KEY,
    tenant="default",
    database="default"
)

embeddings = OpenAIEmbeddings(model= EMBEDDING_MODEL,
                              base_url=OpenAI_base_URL,
                              api_key=OPENAI_API_KEY)
vector_store = Chroma(
    client=chroma_client,
    collection_name="serverless_rag",
    embedding_function=embeddings
)

retriever = vector_store.as_retriever(search_kwargs={"k": 3})

template = "Answer the question based only on the context:\nContext:\n{context}\n\nQuestion: {question}"
prompt = ChatPromptTemplate.from_template(template)

def format_docs(docs):
    return "\n".join(doc.page_content for doc in docs)

def add_chunks(chunks: list[str],  bot_id: int):
    vector_store.add_texts(texts=chunks)

def ask_question(question: str) -> str:
    llm = ChatOpenAI(base_url=OpenAI_base_URL,
                     api_key=OPENAI_API_KEY,
                     model="gpt-4o-mini",
                     temperature=0)
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return rag_chain.invoke(question)
