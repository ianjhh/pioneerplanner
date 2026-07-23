import json
import re
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from api_models import SearchFilters

# Use a smarter model for parsing to guarantee accurate JSON schema
PARSER_MODEL = "qwen2.5:7b-instruct"

parser_llm = ChatOllama(
    model=PARSER_MODEL,
    base_url="http://localhost:11434",
    temperature=0.1,
    format="json"
)

PARSER_SYSTEM_PROMPT = """You are a query parser. You MUST output ONLY valid JSON.
Extract constraints from the user's query into this exact JSON format:
{{
  "semantic_query": "the core topic like 'database' or 'software engineering' (leave empty if only filters)",
  "departments": ["CS"] (list of department codes mentioned),
  "available_terms": ["Spring"] (list of terms mentioned, e.g. Fall, Spring, Summer),
  "exclude_prerequisites": ["CS 301"] (list of EXACT course codes they do NOT want as prerequisites),
  "min_course_level": 300 (integer, see rules below, else null),
  "max_course_level": 499 (integer, see rules below, else null)
}}

COURSE LEVEL RULES:
- "Year 1" or "1st year" or "freshman" -> min: 100, max: 199
- "Year 2" or "2nd year" or "sophomore" -> min: 200, max: 299
- "Year 3" or "3rd year" or "junior" -> min: 300, max: 399
- "Year 4" or "4th year" or "senior" -> min: 400, max: 499
- "Graduate" or "master" -> min: 500, max: 699
- "Upper division" -> min: 300, max: 499
- "Lower division" -> min: 100, max: 299

Example Query: "what cs course does not require cs301 as prerequisite and is 3rd or 4th year"
Example Output:
{{
  "semantic_query": "",
  "departments": ["CS"],
  "available_terms": [],
  "exclude_prerequisites": ["CS 301"],
  "min_course_level": 300,
  "max_course_level": 499
}}

Example Query: "what course is year 1"
Example Output:
{{
  "semantic_query": "",
  "departments": [],
  "available_terms": [],
  "exclude_prerequisites": [],
  "min_course_level": 100,
  "max_course_level": 199
}}
"""

async def parse_natural_language_query(query: str) -> SearchFilters:
    if not query or not query.strip():
        return SearchFilters(semantic_query="")

    try:
        prompt = ChatPromptTemplate.from_messages([
            ("system", PARSER_SYSTEM_PROMPT),
            ("human", "{query}")
        ])
        
        chain = prompt | parser_llm
        result = await chain.ainvoke({"query": query})
        
        # Parse JSON
        content = result.content.strip()
        # Find JSON block in case there's surrounding text
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            json_str = match.group(0)
            data = json.loads(json_str)
            return SearchFilters(**data)
            
    except Exception as e:
        print(f"[WARNING] Query parsing failed: {e}")
        
    return SearchFilters(semantic_query=query)
