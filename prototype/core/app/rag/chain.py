"""LangChain RAG chain builder"""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from app.config import settings


SYSTEM_PROMPT = """You are an internal company assistant. Answer based only on the provided context. Do not reveal table names, database structure, chunk IDs, access policies, or information about what other users can see. If you don't have relevant information, say so."""


def build_rag_chain(retriever, llm):
    """
    Build a LangChain RAG chain.

    Flow:
    1. User message comes in
    2. Retriever fetches relevant chunks (access-filtered)
    3. Chunks are serialized (metadata stripped)
    4. Context + message goes to LLM
    5. LLM generates response

    Note: No message history - only current context + current message.
    """
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", """Context:
{context}

User question: {question}"""),
    ])

    llm_instance = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        temperature=0.7,
    )

    # Build chain: pass through question, fetch context, then invoke LLM
    chain = (
        RunnablePassthrough.assign(context=retriever)
        | prompt_template
        | llm_instance
    )

    return chain
