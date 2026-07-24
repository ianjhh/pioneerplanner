import os
import json
from typing import List, Optional, Set, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from langchain_ollama import OllamaEmbeddings
from tenacity import retry, stop_after_attempt, wait_exponential

from api_models import (
    CourseSearchResult,
    CourseDetailResponse,
    DirectPrereq,
    PrereqTreeNode,
    PrereqPathResponse,
    SearchFilters
)

# Configuration for Ollama embeddings engine matching run.py
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Global embeddings engine instance
embeddings_engine = OllamaEmbeddings(
    model=OLLAMA_EMBED_MODEL,
    base_url=OLLAMA_BASE_URL,
)


@retry(stop=stop_after_attempt(1), wait=wait_exponential(multiplier=1, min=1, max=2), reraise=True)
async def get_embedding_with_retry(query: str):
    return await embeddings_engine.aembed_query(query)

async def vector_search_courses(
    session: AsyncSession,
    filters: SearchFilters,
    limit: int = 5,
    offset: int = 0
) -> Tuple[List[CourseSearchResult], int]:
    """
    Performs Hybrid Search (Vector + Keyword) combined with Reciprocal Rank Fusion (RRF),
    applying strict logical filters.
    """
    query = filters.semantic_query
    department = filters.departments[0] if filters.departments else None
    
    # 1. Compute embedding vector with retry logic
    embedding_str = None
    if query and query.strip():
        try:
            query_vector = await get_embedding_with_retry(query)
            embedding_str = str(query_vector)
        except Exception as e:
            print(f"[WARNING] Vector embedding failed ({type(e).__name__}). Falling back to keyword search.")

    # 2. Build Keyword Search & Hard Filters (WHERE clauses)
    hard_filters = []
    params = {}

    if department:
        hard_filters.append("LOWER(department) = LOWER(:department)")
        params["department"] = department
        
    if filters.available_terms:
        # Postgres array overlap operator && to check if any of the available_terms match
        hard_filters.append("availability && :terms")
        params["terms"] = filters.available_terms
        
    if filters.min_course_level is not None:
        # Extract numeric part of course_id (e.g., '301' from 'CS 301') and compare
        hard_filters.append("CAST(SUBSTRING(course_id FROM '[0-9]+') AS INTEGER) >= :min_level")
        params["min_level"] = filters.min_course_level
        
    if filters.max_course_level is not None:
        hard_filters.append("CAST(SUBSTRING(course_id FROM '[0-9]+') AS INTEGER) <= :max_level")
        params["max_level"] = filters.max_course_level
        
    if filters.exclude_prerequisites:
        # Exclude courses where target_course_id has these as prerequisites
        # Convert to tuple for IN clause
        hard_filters.append("""
            course_id NOT IN (
                SELECT target_course_id FROM prerequisites 
                WHERE prereq_course_id = ANY(:exclude_prereqs)
            )
        """)
        params["exclude_prereqs"] = filters.exclude_prerequisites

    kw_where_clauses = list(hard_filters)
    if query and query.strip():
        kw_where_clauses.append("""
            (
                search_vector @@ plainto_tsquery('english', :query) 
                OR LOWER(course_id) LIKE LOWER(:pattern) 
                OR LOWER(title) LIKE LOWER(:pattern)
            )
        """)
        params["query"] = query
        params["pattern"] = f"%{query}%"
        rank_select = "ts_rank(search_vector, plainto_tsquery('english', :query)) as rank"
        order_by = "ORDER BY rank DESC"
    else:
        rank_select = "0 as rank"
        order_by = ""

    kw_where_str = " AND ".join(kw_where_clauses) if kw_where_clauses else "1=1"
        
    count_sql = text(f"""
        SELECT COUNT(*)
        FROM courses
        WHERE {kw_where_str}
    """)
    count_result = await session.execute(count_sql, params)
    total_count = count_result.scalar() or 0

    # If no criteria provided at all, return empty
    if kw_where_str == "1=1" and not embedding_str:
        return [], 0

    db_limit = limit + offset if embedding_str else limit
    db_offset = 0 if embedding_str else offset
    
    kw_params = dict(params)
    kw_params["db_limit"] = 200 if embedding_str else db_limit
    kw_params["db_offset"] = db_offset

    keyword_sql = text(f"""
        SELECT course_id, title, department, units, description, availability, {rank_select}
        FROM courses
        WHERE {kw_where_str}
        {order_by}
        LIMIT :db_limit OFFSET :db_offset;
    """)
    kw_result = await session.execute(keyword_sql, kw_params)
    kw_rows = kw_result.fetchall()
    
    # 3. Vector Search
    vec_rows = []
    if embedding_str:
        vec_where_clauses = ["embedding IS NOT NULL"]
        if hard_filters:
            vec_where_clauses.extend(hard_filters)
            
        vec_where_str = " AND ".join(vec_where_clauses)
        vec_params = dict(params)
        vec_params["embedding"] = embedding_str
        vec_params["db_limit"] = 200 # Candidate pool size

        vec_sql = text(f"""
            SELECT course_id, title, department, units, description, availability,
                   1 - (embedding <=> :embedding) AS similarity
            FROM courses
            WHERE {vec_where_str}
            ORDER BY embedding <=> :embedding
            LIMIT :db_limit;
        """)
        vec_result = await session.execute(vec_sql, vec_params)
        vec_rows = vec_result.fetchall()

    # 4. Reciprocal Rank Fusion (RRF)
    # If no query string, we don't need RRF, just return DB rows directly
    if not query or not query.strip():
        return [
            CourseSearchResult(
                course_id=row.course_id,
                title=row.title,
                department=row.department,
                units=row.units,
                description=row.description or "",
                availability=row.availability or [],
                similarity_score=1.0
            ) for row in kw_rows
        ], total_count

    k = 60
    rrf_scores = {}
    course_data = {}

    for rank, row in enumerate(kw_rows):
        cid = row.course_id
        rrf_scores[cid] = rrf_scores.get(cid, 0) + (1.0 / (k + rank + 1))
        course_data[cid] = row

    for rank, row in enumerate(vec_rows):
        cid = row.course_id
        base_sim = float(row.similarity) if hasattr(row, 'similarity') else 0
        rrf_scores[cid] = rrf_scores.get(cid, 0) + (1.0 / (k + rank + 1)) + (base_sim * 0.01)
        course_data[cid] = row

    # Sort by RRF score descending
    sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Ensure total_count isn't lower than the candidates we actually found
    # (since vector search candidates might exceed strict keyword matches)
    total_count = max(total_count, len(sorted_results))
    
    # Apply offset and limit after ranking
    paginated_results = sorted_results[offset : offset + limit]

    search_results = []
    for cid, score in paginated_results:
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

    return search_results, total_count


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
    topological course sequence required to take target_course_id using a Recursive CTE.
    """
    target_course = await get_course_detail(session, target_course_id)
    if not target_course:
        return None

    # Recursive CTE to fetch all prerequisite edges in one query
    cte_sql = text("""
        WITH RECURSIVE prereq_tree AS (
            SELECT 
                p.prereq_course_id,
                p.target_course_id,
                p.logic_type,
                p.minimum_grade,
                1 as depth
            FROM prerequisites p
            WHERE LOWER(p.target_course_id) = LOWER(:target_course_id)
            
            UNION
            
            SELECT 
                p.prereq_course_id,
                p.target_course_id,
                p.logic_type,
                p.minimum_grade,
                pt.depth + 1
            FROM prerequisites p
            INNER JOIN prereq_tree pt ON LOWER(p.target_course_id) = LOWER(pt.prereq_course_id)
            WHERE pt.depth < 10
        )
        SELECT 
            pt.prereq_course_id, pt.target_course_id, pt.logic_type, pt.minimum_grade,
            c.title, c.units
        FROM prereq_tree pt
        LEFT JOIN courses c ON LOWER(pt.prereq_course_id) = LOWER(c.course_id);
    """)
    cte_res = await session.execute(cte_sql, {"target_course_id": target_course_id})
    edges = cte_res.fetchall()

    from collections import defaultdict
    children_map = defaultdict(list)
    course_info = {}
    
    all_required_courses = set()
    for row in edges:
        target = row.target_course_id.upper()
        prereq = row.prereq_course_id.upper()
        all_required_courses.add(prereq)
        children_map[target].append(row)
        if prereq not in course_info:
            course_info[prereq] = {"title": row.title, "units": row.units}

    visited_in_path: Set[str] = set()
    topological_sequence: List[str] = []

    def build_tree_node(course_code: str, logic_type: Optional[str] = None, min_grade: Optional[str] = None) -> PrereqTreeNode:
        code_upper = course_code.upper()
        
        # Get metadata
        if code_upper == target_course_id.upper():
            title = target_course.title
            units = target_course.units
        else:
            info = course_info.get(code_upper, {})
            title = info.get("title")
            units = info.get("units")

        if code_upper in visited_in_path:
            return PrereqTreeNode(course_id=course_code, title=title, units=units, logic_type=logic_type, minimum_grade=min_grade, prerequisites=[])

        visited_in_path.add(code_upper)

        child_nodes = []
        for edge in children_map.get(code_upper, []):
            child_node = build_tree_node(edge.prereq_course_id, logic_type=edge.logic_type, min_grade=edge.minimum_grade)
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

    tree_root = build_tree_node(target_course.course_id)

    return PrereqPathResponse(
        target_course_id=target_course.course_id,
        total_courses_required=len(all_required_courses),
        recommended_sequence=topological_sequence,
        prerequisite_tree=tree_root
    )
