import os
import json
from typing import List, Optional, Set, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from langchain_ollama import OllamaEmbeddings
from tenacity import retry, stop_after_attempt, wait_exponential

from api_models import (
    CourseSearchResult,
    CourseDetailResponse,
    DirectPrereq,
    PrereqTreeNode,
    PrereqPathResponse
)

# Configuration for Ollama embeddings engine matching run.py
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Global embeddings engine instance
embeddings_engine = OllamaEmbeddings(
    model=OLLAMA_EMBED_MODEL,
    base_url=OLLAMA_BASE_URL,
)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_embedding_with_retry(query: str):
    return await embeddings_engine.aembed_query(query)

async def vector_search_courses(
    session: AsyncSession,
    query: str,
    limit: int = 5,
    department: Optional[str] = None
) -> List[CourseSearchResult]:
    """
    Performs Hybrid Search (Vector + Keyword) combined with Reciprocal Rank Fusion (RRF).
    """
    # 1. Compute embedding vector with retry logic (Tenacity)
    try:
        query_vector = await get_embedding_with_retry(query)
        embedding_str = str(query_vector)
    except Exception as e:
        print(f"⚠️ Vector embedding failed after retries ({e}).")
        embedding_str = None

    # 2. Keyword Search (ILIKE)
    keyword_sql = text("""
        SELECT course_id, title, department, units, description, availability
        FROM courses
        WHERE (LOWER(title) LIKE LOWER(:pattern) 
               OR LOWER(course_id) LIKE LOWER(:pattern)
               OR LOWER(description) LIKE LOWER(:pattern))
          AND (:department IS NULL OR LOWER(department) = LOWER(:department))
        LIMIT 50;
    """)
    kw_result = await session.execute(keyword_sql, {"pattern": f"%{query}%", "department": department})
    kw_rows = kw_result.fetchall()
    
    # 3. Vector Search
    vec_rows = []
    if embedding_str:
        vec_sql = text("""
            SELECT course_id, title, department, units, description, availability,
                   1 - (embedding <=> :embedding) AS similarity
            FROM courses
            WHERE embedding IS NOT NULL
              AND (:department IS NULL OR LOWER(department) = LOWER(:department))
            ORDER BY embedding <=> :embedding
            LIMIT 50;
        """)
        vec_result = await session.execute(vec_sql, {"embedding": embedding_str, "department": department, "limit": limit})
        vec_rows = vec_result.fetchall()

    # 4. Reciprocal Rank Fusion (RRF)
    # RRF Score = 1 / (k + rank)
    k = 60
    rrf_scores = {}
    course_data = {}

    for rank, row in enumerate(kw_rows):
        cid = row.course_id
        rrf_scores[cid] = rrf_scores.get(cid, 0) + (1.0 / (k + rank + 1))
        course_data[cid] = row

    for rank, row in enumerate(vec_rows):
        cid = row.course_id
        # Boost RRF score slightly based on raw vector similarity if available
        base_sim = float(row.similarity) if hasattr(row, 'similarity') else 0
        rrf_scores[cid] = rrf_scores.get(cid, 0) + (1.0 / (k + rank + 1)) + (base_sim * 0.01)
        course_data[cid] = row

    # Sort by RRF score descending
    sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:limit]

    search_results = []
    for cid, score in sorted_results:
        row = course_data[cid]
        search_results.append(
            CourseSearchResult(
                course_id=row.course_id,
                title=row.title,
                department=row.department,
                units=row.units,
                description=row.description or "",
                availability=row.availability or [],
                similarity_score=round(score, 4)
            )
        )

    return search_results


async def get_course_detail(
    session: AsyncSession,
    course_id: str
) -> Optional[CourseDetailResponse]:
    """
    Fetches details for a single course along with its immediate prerequisites.
    """
    # Query course
    course_sql = text("""
        SELECT course_id, title, department, units, description, availability
        FROM courses
        WHERE LOWER(course_id) = LOWER(:course_id);
    """)
    course_res = await session.execute(course_sql, {"course_id": course_id})
    course_row = course_res.fetchone()

    if not course_row:
        return None

    # Query direct prerequisites
    prereq_sql = text("""
        SELECT p.prereq_course_id, p.logic_type, p.minimum_grade, c.title, c.units
        FROM prerequisites p
        LEFT JOIN courses c ON LOWER(p.prereq_course_id) = LOWER(c.course_id)
        WHERE LOWER(p.target_course_id) = LOWER(:course_id);
    """)
    prereq_res = await session.execute(prereq_sql, {"course_id": course_id})
    prereq_rows = prereq_res.fetchall()

    direct_prereqs = [
        DirectPrereq(
            prereq_course_id=p.prereq_course_id,
            logic_type=p.logic_type,
            minimum_grade=p.minimum_grade or "C",
            title=p.title,
            units=p.units
        )
        for p in prereq_rows
    ]

    return CourseDetailResponse(
        course_id=course_row.course_id,
        title=course_row.title,
        department=course_row.department,
        units=course_row.units,
        description=course_row.description or "",
        availability=course_row.availability or [],
        direct_prerequisites=direct_prereqs
    )


async def get_prerequisite_path(
    session: AsyncSession,
    target_course_id: str
) -> Optional[PrereqPathResponse]:
    """
    Computes the complete recursive prerequisite dependency graph and recommended
    topological course sequence required to take target_course_id.
    """
    # 1. Fetch target course info
    target_course = await get_course_detail(session, target_course_id)
    if not target_course:
        return None

    # Track visited courses to avoid infinite loops on cyclical catalog edge data
    visited_in_path: Set[str] = set()
    all_required_courses: Set[str] = set()
    topological_sequence: List[str] = []

    async def build_tree_node(course_code: str, logic_type: Optional[str] = None, min_grade: Optional[str] = None) -> PrereqTreeNode:
        code_upper = course_code.upper()

        # Fetch metadata
        c_detail = await get_course_detail(session, course_code)
        title = c_detail.title if c_detail else None
        units = c_detail.units if c_detail else None

        if code_upper in visited_in_path:
            # Prevent circular reference recursion break
            return PrereqTreeNode(
                course_id=course_code,
                title=title,
                units=units,
                logic_type=logic_type,
                minimum_grade=min_grade,
                prerequisites=[]
            )

        visited_in_path.add(code_upper)

        child_nodes = []
        if c_detail and c_detail.direct_prerequisites:
            for p in c_detail.direct_prerequisites:
                prereq_code = p.prereq_course_id
                all_required_courses.add(prereq_code.upper())
                child_node = await build_tree_node(
                    prereq_code,
                    logic_type=p.logic_type,
                    min_grade=p.minimum_grade
                )
                child_nodes.append(child_node)

        visited_in_path.remove(code_upper)

        if code_upper != target_course_id.upper() and code_upper not in topological_sequence:
            topological_sequence.append(course_code)

        return PrereqTreeNode(
            course_id=course_code,
            title=title,
            units=units,
            logic_type=logic_type,
            minimum_grade=min_grade,
            prerequisites=child_nodes
        )

    tree_root = await build_tree_node(target_course.course_id)

    return PrereqPathResponse(
        target_course_id=target_course.course_id,
        total_courses_required=len(all_required_courses),
        recommended_sequence=topological_sequence,
        prerequisite_tree=tree_root
    )
