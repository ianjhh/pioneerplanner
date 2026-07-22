"use client";

import { useState } from "react";
import { Search, Loader2 } from "lucide-react";
import Link from "next/link";
import { CourseSearchResult } from "@/types/api";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CourseSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError("");

    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/search?q=${encodeURIComponent(query)}`);
      if (!res.ok) throw new Error("Search request failed");
      const data = await res.json();
      setResults(Array.isArray(data.results) ? data.results : []);
    } catch (err: any) {
      setError(err.message || "An error occurred");
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center max-w-4xl mx-auto py-12">
      <div className="w-full text-center mb-12">
        <h1 className="text-4xl md:text-5xl font-extrabold text-gray-900 tracking-tight mb-4">
          Discover Your Academic Path
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          Search for courses across the catalog and explore prerequisites instantly using semantic AI.
        </p>
      </div>

      <form onSubmit={handleSearch} className="w-full max-w-2xl relative">
        <div className="relative flex items-center">
          <input
            type="text"
            className="w-full pl-12 pr-24 py-4 rounded-full border border-gray-300 focus:outline-none focus:ring-4 focus:ring-indigo-500/20 focus:border-indigo-500 shadow-sm transition-all text-lg"
            placeholder="Search for 'Machine Learning', 'CS 321'..."
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
                <span className="inline-block px-3 py-1 bg-indigo-50 text-indigo-700 text-sm font-semibold rounded-full mb-2">
                  {course.course_id}
                </span>
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
    </div>
  );
}
