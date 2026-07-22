export interface CourseSearchResult {
  course_id: string;
  title: string;
  department: string;
  units: string;
  description: string;
  availability: string[];
  similarity_score?: number;
}

export interface DirectPrereq {
  prereq_course_id: string;
  logic_type?: string;
  minimum_grade: string;
  title?: string;
  units?: string;
}

export interface CourseDetailResponse extends CourseSearchResult {
  direct_prerequisites: DirectPrereq[];
}

export interface PrereqTreeNode {
  course_id: string;
  title?: string;
  units?: string;
  logic_type?: string;
  minimum_grade?: string;
  prerequisites: PrereqTreeNode[];
}

export interface PrereqPathResponse {
  target_course_id: string;
  total_courses_required: number;
  recommended_sequence: string[];
  prerequisite_tree: PrereqTreeNode;
}

export interface ChatMessage {
  sender: 'user' | 'ai';
  text: string;
}
