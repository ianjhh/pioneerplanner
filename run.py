import asyncio
from agent import compiled_agent

async def main():
    # Complex, non-linear text mock representing a typical raw university catalog scrape
    sample_catalog_entry = """
    Department of Computer Science. Course Num: CS 321. Title: Advanced Software Engineering. 
    Units: 4. This course explores advanced software system developments. 
    Prerequisites: Students must complete CS 301 and either CS 311 or MATH 230 with a 
    minimum grade of C. Furthermore, do not enroll if you haven't passed CS 321 previously.
    """
    
    print("🚀 Initializing LangGraph Extraction Runner Instance...")
    
    # Prepare the initial state machine dictionary container
    initial_state = {
        "raw_text": sample_catalog_entry,
        "extracted_course": None,
        "error_message": None,
        "retry_count": 0
    }
    
    # Execute the agent graph asynchronously
    final_state = await compiled_agent.ainvoke(initial_state)
    
    print("\n================ FINAL ARCHITECTURE OUTPUT ================")
    if final_state.get("extracted_course"):
        # Pydantic's model_dump_json prints out beautiful, format-validated JSON
        print(final_state["extracted_course"].model_dump_json(indent=2))
    else:
        print("Pipeline failed to securely extract metadata.")
        print(f"Final logged state error details: {final_state['error_message']}")

if __name__ == "__main__":
    asyncio.run(main())