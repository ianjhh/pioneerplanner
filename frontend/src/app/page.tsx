"use client";

import { useState, useEffect } from "react";
import { Search, Loader2 } from "lucide-react";
import Link from "next/link";
import { CourseSearchResult } from "@/types/api";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [department, setDepartment] = useState("");
  const [results, setResults] = useState<CourseSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  // Pagination State
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  const LIMIT = 20;

  const fetchCourses = async (searchQuery: string, dept: string, pageNum: number) => {
    if (!searchQuery.trim() && !dept) return;
    setLoading(true);
    setError("");

    try {
      const offset = (pageNum - 1) * LIMIT;
      let url = `http://127.0.0.1:8000/api/v1/search?limit=${LIMIT}&offset=${offset}`;
      
      if (searchQuery.trim()) {
        url += `&q=${encodeURIComponent(searchQuery)}`;
      }
      if (dept) {
        url += `&department=${encodeURIComponent(dept)}`;
      }

      const res = await fetch(url);
      if (!res.ok) throw new Error("Search request failed");
      const data = await res.json();
      const fetchedResults = Array.isArray(data.results) ? data.results : [];
      
      setResults(fetchedResults);
      setTotalCount(data.total_count || 0);
      setHasMore(offset + fetchedResults.length < (data.total_count || 0));
    } catch (err: any) {
      setError(err.message || "An error occurred");
      setResults([]);
      setTotalCount(0);
      setHasMore(false);
    } finally {
      setLoading(false);
    }
  };

  // Automatically fetch initial courses on load
  useEffect(() => {
    setDepartment("CS");
    fetchCourses("", "CS", 1);
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setDepartment("");
    fetchCourses(query, "", 1);
  };

  const handleTagClick = (label: string, dept: string) => {
    setQuery(label);
    setDepartment(dept);
    setPage(1);
    fetchCourses("", dept, 1);
  };

  const handleNextPage = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    fetchCourses(query, department, nextPage);
  };

  const handlePrevPage = () => {
    const prevPage = Math.max(1, page - 1);
    setPage(prevPage);
    fetchCourses(query, department, prevPage);
  };

  return (
    <div className="flex flex-col items-center max-w-4xl mx-auto py-12">
      <div className="w-full text-center mb-8">
        <h1 className="text-4xl md:text-5xl font-extrabold text-gray-900 tracking-tight mb-4">
          Discover Your Academic Path
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          Search over 2,700+ CSU East Bay catalog courses across all departments and explore prerequisite dependencies.
        </p>
      </div>

      <form onSubmit={handleSearch} className="w-full max-w-2xl relative mb-6">
        <div className="relative flex items-center">
          <input
            type="text"
            className="w-full pl-12 pr-24 py-4 rounded-full border border-gray-300 focus:outline-none focus:ring-4 focus:ring-indigo-500/20 focus:border-indigo-500 shadow-sm transition-all text-lg text-gray-900"
            placeholder="e.g. Give me a course related to database, or what is the prerequisite of CS 301?"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <Search className="absolute left-4 text-gray-400 w-6 h-6" />
          <button
            type="submit"
            disabled={loading}
            className="absolute right-2 top-2 bottom-2 px-6 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-full transition-colors disabled:opacity-70 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Search"}
          </button>
        </div>
      </form>

      {/* Quick Filter Chips */}
      <div className="flex flex-wrap justify-center gap-2 mb-8 max-w-2xl">
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider self-center mr-2">Popular:</span>
        {[
          { label: "CS", dept: "CS" },
          { label: "Computer Science", dept: "CS" },
          { label: "BIOL", dept: "BIOL" },
          { label: "MATH", dept: "MATH" },
          { label: "NURS", dept: "NURS" },
          { label: "KIN", dept: "KIN" },
          { label: "ENGL", dept: "ENGL" },
          { label: "ART", dept: "ART" },
          { label: "ACCT", dept: "ACCT" },
          { label: "MGMT", dept: "MGMT" }
        ].map((tag) => (
          <button
            key={tag.label}
            type="button"
            onClick={() => handleTagClick(tag.label, tag.dept)}
            className="px-3 py-1.5 bg-gray-100 hover:bg-indigo-50 hover:text-indigo-600 text-gray-600 text-xs font-medium rounded-full transition-colors"
          >
            {tag.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="mt-8 p-4 bg-red-50 text-red-700 rounded-xl w-full max-w-2xl border border-red-100">
          {error}
        </div>
      )}

      <div className="mt-12 w-full grid grid-cols-1 gap-6">
        {Array.isArray(results) && results.map((course) => (
          <div key={course.course_id} className="bg-white rounded-2xl p-6 shadow-sm border hover:shadow-md transition-shadow group">
            <div className="flex justify-between items-start mb-4">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="inline-block px-3 py-1 bg-indigo-50 text-indigo-700 text-sm font-semibold rounded-full">
                    {course.course_id}
                  </span>
                  {course.similarity_score !== undefined && (
                    <span className="inline-block px-2 py-1 bg-amber-50 text-amber-700 text-xs font-semibold rounded-full border border-amber-200">
                      Relevance Score: {course.similarity_score}
                    </span>
                  )}
                </div>
                <h3 className="text-xl font-bold text-gray-900">{course.title}</h3>
              </div>
              <span className="text-sm font-medium text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                {course.units} Units
              </span>
            </div>
            
            <p className="text-gray-600 text-sm leading-relaxed mb-6 line-clamp-3">
              {course.description}
            </p>
            
            <div className="flex justify-between items-center pt-4 border-t border-gray-100">
              <div className="flex gap-2">
                {course.availability?.map((term) => (
                  <span key={term} className="text-xs font-medium text-emerald-700 bg-emerald-50 px-2 py-1 rounded-md">
                    {term}
                  </span>
                ))}
              </div>
              
              <Link 
                href={`/graph?course=${encodeURIComponent(course.course_id)}`}
                className="text-sm font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 group-hover:translate-x-1 transition-transform"
              >
                View Prerequisites &rarr;
              </Link>
            </div>
          </div>
        ))}
        
        {results.length === 0 && !loading && !error && query.length > 0 && (
          <div className="text-center py-12 text-gray-500">
            No courses found for "{query}". Try a different keyword.
          </div>
        )}
      </div>

      {/* Pagination Controls */}
      {results.length > 0 && (
        <div className="mt-12 flex flex-col items-center gap-4 w-full max-w-2xl">
          <div className="text-sm font-medium text-gray-500">
            Showing {(page - 1) * LIMIT + 1}-{Math.min(page * LIMIT, totalCount)} of {totalCount} courses
          </div>
          <div className="flex items-center justify-center gap-4 w-full">
            <button
              onClick={handlePrevPage}
              disabled={page === 1 || loading}
              className="px-6 py-2.5 bg-white border border-gray-300 text-gray-700 font-medium rounded-full hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              &larr; Previous
            </button>
            <button
              onClick={handleNextPage}
              disabled={!hasMore || loading}
              className="px-6 py-2.5 bg-white border border-gray-300 text-gray-700 font-medium rounded-full hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next &rarr;
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
