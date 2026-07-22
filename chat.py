import os
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

# Configuration for Ollama Chat models
OLLAMA_MODEL_FAST = os.getenv("OLLAMA_MODEL_FAST", "qwen2.5:0.5b-instruct") # For simple routing
OLLAMA_MODEL_COMPLEX = os.getenv("OLLAMA_MODEL_COMPLEX", "qwen2.5:7b-instruct") # For deep reasoning
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Initialize the local Ollama chat clients
llm_fast = ChatOllama(
    model=OLLAMA_MODEL_FAST,
    base_url=OLLAMA_BASE_URL,
    temperature=0.3,
)

llm_complex = ChatOllama(
    model=OLLAMA_MODEL_COMPLEX,
    base_url=OLLAMA_BASE_URL,
    temperature=0.7,
)

def route_model(query: str) -> ChatOllama:
    """
    Stretch Goal: Model Routing based on heuristic complexity.
    """
    complex_keywords = ["why", "compare", "plan", "strategy", "prerequisite", "explain"]
    if any(kw in query.lower() for kw in complex_keywords) or len(query.split()) > 15:
        return llm_complex
    return llm_fast

SYSTEM_PROMPT = """You are PioneerPlanner, a helpful and knowledgeable academic advising assistant for university students. 
You answer questions about courses, prerequisites, and degree planning. 
Base your answers ON THE PROVIDED CONTEXT ONLY. If the answer is not in the context, say you do not know.

Context:
{context}
"""

async def stream_rag_chat(query: str, search_results: list) -> str:
    """
    Generator that yields streaming text from the LLM based on user query and RAG context.
    """
    # Build context from search results
    context_text = ""
    for idx, course in enumerate(search_results):
        context_text += f"\n{idx+1}. {course.course_id}: {course.title} ({course.units} units)\n"
        context_text += f"   Description: {course.description}\n"
        if course.availability:
            context_text += f"   Availability: {', '.join(course.availability)}\n"
            
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{query}")
    ])
    
    selected_llm = route_model(query)
    chain = prompt | selected_llm
    
    async for chunk in chain.astream({"context": context_text, "query": query}):
        yield chunk.content
