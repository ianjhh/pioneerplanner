import uvicorn
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from api_models import (
    SearchResponse,
    CourseDetailResponse,
    PrereqPathResponse
)
from retrieval import (
    vector_search_courses,
    get_course_detail,
    get_prerequisite_path
)

app = FastAPI(
    title="PioneerPlanner API",
    description="Vector Search & Prerequisite Graph Retrieval Backend for University Course Planning",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_db():
    """FastAPI Async DB session dependency provider."""
    async with AsyncSessionLocal() as session:
        yield session


@app.get("/health", summary="Health check endpoint")
async def health_check():
    """Verify backend API service status."""
    return {"status": "ok", "app": "PioneerPlanner API", "version": "1.0.0"}


@app.get("/api/v1/search", response_model=SearchResponse, summary="Vector course search")
async def search_courses(
    q: str = Query(..., min_length=1, description="Natural language search query e.g. 'machine learning' or 'CS 321'"),
    limit: int = Query(default=5, ge=1, le=50, description="Max results to return"),
    department: Optional[str] = Query(default=None, description="Filter by department code e.g. 'CS'"),
    db: AsyncSession = Depends(get_db)
):
    """
    Performs semantic vector similarity search using pgvector over course descriptions.
    """
    results = await vector_search_courses(session=db, query=q, limit=limit, department=department)
    return SearchResponse(
        query=q,
        total_count=len(results),
        results=results
    )


@app.get("/api/v1/courses/{course_id}", response_model=CourseDetailResponse, summary="Get course details & direct prerequisites")
async def read_course(
    course_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves course metadata and immediate prerequisite rules for a given course ID.
    """
    course = await get_course_detail(session=db, course_id=course_id)
    if not course:
        raise HTTPException(
            status_code=404,
            detail=f"Course '{course_id}' not found in catalog."
        )
    return course


@app.get("/api/v1/courses/{course_id}/prereq-path", response_model=PrereqPathResponse, summary="Compute full prerequisite dependency path")
async def read_prerequisite_path(
    course_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Recursively calculates the full prerequisite dependency graph (tree) and
    topologically recommended course completion sequence for target course_id.
    """
    prereq_path = await get_prerequisite_path(session=db, target_course_id=course_id)
    if not prereq_path:
        raise HTTPException(
            status_code=404,
            detail=f"Course '{course_id}' not found in catalog."
        )
    return prereq_path


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
