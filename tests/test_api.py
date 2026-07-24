import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app
from api_models import (
    CourseSearchResult,
    CourseDetailResponse,
    DirectPrereq,
    PrereqPathResponse,
    PrereqTreeNode
)

client = TestClient(app)


class TestPioneerPlannerAPI(unittest.TestCase):

    def test_health_check(self):
        """Verify health check endpoint returns 200 OK."""
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("PioneerPlanner", data["app"])

    @patch("main.vector_search_courses")
    def test_search_courses_endpoint(self, mock_vector_search):
        """Test vector search API route response structure."""
        mock_vector_search.return_value = [
            CourseSearchResult(
                course_id="CS321",
                title="Software Engineering",
                department="Computer Science",
                units=3,
                description="Principles of software engineering and design.",
                availability=["Fall", "Spring"],
                similarity_score=0.9251
            )
        ]

        response = client.get("/api/v1/search?q=software+engineering&department=CS&limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["query"], "software engineering")
        self.assertEqual(data["total_count"], 1)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["course_id"], "CS321")
        self.assertEqual(data["results"][0]["similarity_score"], 0.9251)

    @patch("main.get_course_detail")
    def test_get_course_detail_success(self, mock_get_detail):
        """Test course detail route with valid course ID."""
        mock_get_detail.return_value = CourseDetailResponse(
            course_id="CS321",
            title="Software Engineering",
            department="Computer Science",
            units=3,
            description="Principles of software engineering.",
            availability=["Fall"],
            direct_prerequisites=[
                DirectPrereq(
                    prereq_course_id="CS201",
                    logic_type="AND",
                    minimum_grade="C",
                    title="Data Structures",
                    units=3
                )
            ]
        )

        response = client.get("/api/v1/courses/CS321")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["course_id"], "CS321")
        self.assertEqual(len(data["direct_prerequisites"]), 1)
        self.assertEqual(data["direct_prerequisites"][0]["prereq_course_id"], "CS201")

    @patch("main.get_course_detail")
    def test_get_course_detail_not_found(self, mock_get_detail):
        """Test course detail route with invalid course ID returns 404."""
        mock_get_detail.return_value = None

        response = client.get("/api/v1/courses/NONEXISTENT999")
        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["detail"].lower())

    @patch("main.get_prerequisite_path")
    def test_get_prereq_path_success(self, mock_get_path):
        """Test prerequisite path resolution endpoint."""
        mock_get_path.return_value = PrereqPathResponse(
            target_course_id="CS321",
            total_courses_required=2,
            recommended_sequence=["CS101", "CS201"],
            prerequisite_tree=PrereqTreeNode(
                course_id="CS321",
                title="Software Engineering",
                units=3,
                prerequisites=[
                    PrereqTreeNode(
                        course_id="CS201",
                        title="Data Structures",
                        units=3,
                        logic_type="AND",
                        minimum_grade="C",
                        prerequisites=[
                            PrereqTreeNode(
                                course_id="CS101",
                                title="Intro to CS",
                                units=3,
                                logic_type="AND",
                                minimum_grade="C",
                                prerequisites=[]
                            )
                        ]
                    )
                ]
            )
        )

        response = client.get("/api/v1/courses/CS321/prereq-path")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["target_course_id"], "CS321")
        self.assertEqual(data["total_courses_required"], 2)
        self.assertEqual(data["recommended_sequence"], ["CS101", "CS201"])
        self.assertEqual(data["prerequisite_tree"]["course_id"], "CS321")
        self.assertEqual(len(data["prerequisite_tree"]["prerequisites"]), 1)


if __name__ == "__main__":
    unittest.main()
