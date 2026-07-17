from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class PrerequisiteLogic(BaseModel):
    logic_type: Literal["AND", "OR"] = Field(
        ..., description="The type of logic to apply to the prerequisites (AND or OR)."
        
    )
    courses: List[str] = Field(
        ..., description="A list of course codes that are prerequisites."
    )
    minimum_grade: Optional[str] = Field(
        default="C", description="The minimum grade required for the prerequisites (default is C)."
    )

class CourseModel(BaseModel):
    course_id: str = Field(..., description="Course ID, for example CS321")
    title: str = Field(..., description="Course title, for example 'Software Engineering'")
    department: str = Field(..., description="The issuing department")
    units: int = Field(..., description="Number of credit units")
    description: str = Field(..., description="Course description")

    availability: Optional[List[str]] = Field(
        default=None,
        description=(
            "Terms this course is typically offered in, normalized to a subset of "
            "['Fall', 'Winter', 'Spring', 'Summer']. Leave empty if not stated or unclear."
        )
    )

    prerequisites: Optional[List[PrerequisiteLogic]] = Field(
        default=None, description="Structured prerequisite logic"
    )

# testing input data conversion to structured data using CourseModel
if __name__ == "__main__":
    # If the LLM extracts data, Pydantic ensures it looks exactly like this:
    extracted_data = {
        "course_id": "CS 321",
        "title": "Software Engineering",
        "department": "Computer Science",
        "units": 3,
        "description": "Principles of software engineering. Prerequisite: CS 301 and CS 311.",
        "availability": ["Fall", "Spring"],
        "prerequisites": [
            {
                "logic_type": "AND",
                "courses": ["CS 301", "CS 311"],
                "minimum_grade": "C"
            }
        ]
    }

    validated_course = CourseModel(**extracted_data)
    print(f"Successfully validated: {validated_course.course_id} - {validated_course.title}")