import os
from typing import TypedDict, Optional, Literal

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END

from models import CourseModel

load_dotenv()


class AgentState(TypedDict):
    """
    This class defines the exact shape of the data traveling through our graph.
    Every node receives this state, mutates it, and returns the updated fields.
    """
    raw_text: str  # Input text from the university catalog
    extracted_course: Optional[CourseModel]  # Stores the structured output when successful
    error_message: Optional[str]  # Stores error text if validation fails
    retry_count: int


# Config pulled from env so you can swap models/hosts without touching code.
# OLLAMA_MODEL: any model you've pulled with `ollama pull <model>`.
# qwen3:8b is a solid default for structured extraction on a single 8GB+ GPU.
# Bump to qwen2.5:14b or qwen3:14b if your hardware allows and you want better
# AND/OR prerequisite-tree reasoning.
# OLLAMA_BASE_URL: defaults to the local Ollama server. Change if Ollama runs
# elsewhere (e.g. a Docker service name, or a GPU box on your LAN).
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Initialize the local Ollama client
llm = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_BASE_URL,
    temperature=0,  # Set to 0 to keep the output highly structured and consistent
)

# Bind the target Pydantic schema to the model.
# langchain-ollama's with_structured_output defaults to Ollama's native
# JSON-schema-constrained decoding (requires Ollama >= 0.5), so this works even
# with models that weren't specifically fine-tuned for tool calling.
structured_llm = llm.with_structured_output(CourseModel)


async def extraction_node(state: AgentState) -> AgentState:
    """
    Node 1: Prompt the LLM and bind the structured response to the state.
    """
    print(f"\n[Node: Extraction] Attempting extraction. Retry count: {state['retry_count']}")

    # System prompt using our safety {error_feedback} placeholder to avoid brackets parsing bug
    system_prompt = (
        "You are an advanced university registrar agent. Your job is to parse unstructured "
        "course details into precise structural data models. Pay extreme attention to "
        "prerequisite logic rules (AND/OR trees).\n\n"
        "{error_feedback}"
    )

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Extract the structured details from this raw course text:\n\n{catalog_text}")
    ])

    extraction_chain = prompt_template | structured_llm

    # Formulate error feedback if we are on a retry loop
    error_feedback = ""
    if state["error_message"]:
        error_feedback = (
            f"CRITICAL FIX REQUIRED: Your previous attempt failed validation with this error:\n"
            f"{state['error_message']}\n"
            f"Correct your structural layout accordingly."
        )

    try:
        result: CourseModel = await extraction_chain.ainvoke({
            "catalog_text": state["raw_text"],
            "error_feedback": error_feedback
        })
        return {
            "extracted_course": result,
            "error_message": None  # Reset error message on success
        }
    except Exception as e:
        return {
            "extracted_course": None,  # clear any stale course left from a prior attempt
            "error_message": str(e),
            "retry_count": state["retry_count"] + 1
        }


async def validation_node(state: AgentState) -> AgentState:
    """
    Node 2: Validates extracted data against semantic rules.
    """
    print("[Node: Validation] Inspecting data logic constraints...")

    course = state.get("extracted_course")
    if not course:
        return state

    # Example Rule: A course cannot list itself as its own prerequisite.
    if course.prerequisites:
        for group in course.prerequisites:
            if course.course_id in group.courses:
                error_txt = f"Course '{course.course_id}' cannot become its own prerequisite."
                return {
                    "error_message": error_txt,
                    "retry_count": state["retry_count"] + 1
                }

    print("✅ Validation node passed successfully.")
    return state


def route_post_validation(state: AgentState) -> Literal["extraction_node", "__end__"]:
    """
    Conditional routing path selector based on the state results.
    """
    if state["error_message"] and state["retry_count"] < 3:
        print(f"Routing Rule: Retrying due to validation error: {state['error_message']}")
        return "extraction_node"

    print("Routing Rule: Terminating state workflow execution.")
    return "__end__"


# Graph configuration Setup
workflow = StateGraph(AgentState)
workflow.add_node("extraction_node", extraction_node)
workflow.add_node("validation_node", validation_node)

workflow.add_edge(START, "extraction_node")
workflow.add_edge("extraction_node", "validation_node")
workflow.add_conditional_edges(
    "validation_node",
    route_post_validation
)

compiled_agent = workflow.compile()