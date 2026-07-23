from pydantic import BaseModel, Field
from typing import List, Optional

class CourseBase(BaseModel):
    course_id: str = Field(..., description="Course code/identifier e.g. 'CS321' or 'CS 321'")
    title: str = Field(..., description="Course title")
    department: str = Field(..., description="Department name")
    units: int = Field(..., description="Credit units")
    description: str = Field(..., description="Course description")
    availability: Optional[List[str]] = Field(default=None, description="Terms available (Fall, Spring, etc.)")

class CourseSearchResult(CourseBase):
    similarity_score: float = Field(..., description="Vector similarity score (0.0 to 1.0)")

class SearchFilters(BaseModel):
    semantic_query: str = Field(default="", description="The core concept or topic to search for using vector search. Omit constraints like 'Spring' or 'CS 301' from this string.")
    departments: List[str] = Field(default_factory=list, description="List of department codes (e.g. ['CS', 'MATH'])")
    available_terms: List[str] = Field(default_factory=list, description="List of terms (e.g. ['Spring', 'Fall'])")
    exclude_prerequisites: List[str] = Field(default_factory=list, description="List of course codes that should NOT be prerequisites (e.g. ['CS 301'])")
    min_course_level: Optional[int] = Field(default=None, description="Minimum course level (e.g. 300 for 3rd year)")
    max_course_level: Optional[int] = Field(default=None, description="Maximum course level (e.g. 499 for 4th year)")

class SearchResponse(BaseModel):
    query: str = Field(..., description="The input search query")
    total_count: int = Field(..., description="Number of results returned")
    results: List[CourseSearchResult] = Field(..., description="Ranked list of matching courses")

class DirectPrereq(BaseModel):
    prereq_course_id: str = Field(..., description="Prerequisite course code")
    logic_type: str = Field(..., description="'AND' or 'OR'")
    minimum_grade: str = Field(default="C", description="Minimum grade required")
    title: Optional[str] = Field(default=None, description="Prerequisite course title if available")
    units: Optional[int] = Field(default=None, description="Prerequisite course units if available")

class CourseDetailResponse(CourseBase):
    direct_prerequisites: List[DirectPrereq] = Field(default_factory=list, description="Immediate prerequisites")

class PrereqTreeNode(BaseModel):
    course_id: str = Field(..., description="Course code")
    title: Optional[str] = Field(default=None, description="Course title")
    units: Optional[int] = Field(default=None, description="Course credit units")
    logic_type: Optional[str] = Field(default=None, description="Requirement logic relative to parent ('AND' / 'OR')")
    minimum_grade: Optional[str] = Field(default=None, description="Minimum grade required")
    prerequisites: List['PrereqTreeNode'] = Field(default_factory=list, description="Sub-prerequisites required for this course")

# Re-build model to resolve recursive type reference
PrereqTreeNode.model_rebuild()

class PrereqPathResponse(BaseModel):
    target_course_id: str = Field(..., description="Target course ID")
    total_courses_required: int = Field(..., description="Total unique prerequisite courses in dependency chain")
    recommended_sequence: List[str] = Field(..., description="Topologically sorted sequence of courses to complete prerequisites")
    prerequisite_tree: PrereqTreeNode = Field(..., description="Hierarchical prerequisite tree")
