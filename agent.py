import os
from typing import TypedDict, Optional, Literal
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from models import CourseModel

load_dotenv()

class AgentState(TypedDict):
    """
    This class defines the exact shape of the data traveling through our graph.
    Every node receives this state, mutates it, and returns the updated fields.
    """
    raw_text: str                           # Input text from the university catalog
    extracted_course: Optional[CourseModel] # Stores the structured output when successful
    error_message: Optional[str]            # Stores error text if validation fails
    retry_count: int

#temperature to 0 for consistent output
llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0.0)

# .with_structured_output() tells LLM 
# to run our Pydantic model as a structural constraint via native tool-calling primitives.
structured_llm = llm.with_structured_output(CourseModel)

async def extraction_node(state: AgentState) -> AgentState:
    """
    Node 1: Responsible for prompting the LLM and binding the response to the state.
    """
    print(f"\n[Node: Extraction] Attempting extraction. Retry count: {state['retry_count']}")

    # Base extraction prompt
    system_prompt = (
        "You are an advanced university registrar agent. Your job is to parse unstructured "
        "course details into precise structural data models. Pay extreme attention to "
        "prerequisite logic rules (AND/OR trees)."
    )

    # If this is a retry attempt, send error back into prompt
    if state["error_message"]:
        system_prompt += f"\n\n CRITICAL FIX REQUIRED: Your previous attempt failed validation with this error: {state['error_message']}. Correct your structural layout."

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Extract the structured details from this raw course text:\n\n{catalog_text}")
    ])

    # Chain the prompt together with llm instance
    extraction_chain = prompt_template | structured_llm

    try:
        # Invoke the chain asynchronously
        result: CourseModel = await extraction_chain.ainvoke({"catalog_text": state["raw_text"]})
        
        # Return updates to the state. LangGraph automatically merges this dict into the main state.
        return {
            "extracted_course": result,
            "error_message": None # Reset error message if the LLM successfully outputted valid JSON
        }
    except Exception as e:
        # Catch JSON structure errors or LLM timeouts before they crash the application
        return {
            "error_message": str(e),
            "retry_count": state["retry_count"] + 1
        }
    
async def validation_node(state: AgentState) -> AgentState:
    """
    Node 2: Validates extracted data
    """
    print("[Node: Validation] Inspecting data logic constraints...")
    course = state.get("extracted_course")
    
    # Fallback if the extraction node crashed internally and passed no course data
    if not course:
        return state 

    # Custom semantic validation rule: A course cannot be its own prerequisite.
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
    Determines where the state machine routes next based on data health.
    """
    # If an error exists and we haven't crossed our budget limit, route back to extraction
    if state["error_message"] and state["retry_count"] < 3:
        print(f"Routing Rule triggered: Retrying due to validation error: {state['error_message']}")
        return "extraction_node"
    
    # If data is correct OR we hit our safety limit, exit the graph
    print("Routing Rule triggered: Terminating state workflow execution.")
    return "__end__"

# Initialize the graph framework passing our state schema contract
workflow = StateGraph(AgentState)

# Append nodes
workflow.add_node("extraction_node", extraction_node)
workflow.add_node("validation_node", validation_node)

# Set the starting point entry gate
workflow.add_edge(START, "extraction_node")

# Pipe output from extraction directly over into validation
workflow.add_edge("extraction_node", "validation_node")

# tells LangGraph "after validation_node runs, don't just go to one fixed next step; instead, call a function to decide where to go."
workflow.add_conditional_edges(
    "validation_node",
    route_post_validation
)

# Compile the execution pipeline map
compiled_agent = workflow.compile()