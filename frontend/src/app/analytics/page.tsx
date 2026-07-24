"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Loader2 } from "lucide-react";

interface Bottleneck {
  course_id: string;
  title: string;
  dependency_count: number;
}

export default function AnalyticsPage() {
  const [bottlenecks, setBottlenecks] = useState<Bottleneck[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8000/api/v1/analytics/bottlenecks?limit=10");
        if (!res.ok) throw new Error("Failed to fetch analytics");
        const data = await res.json();
        setBottlenecks(data.bottlenecks || []);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, []);

  return (
    <div className="flex flex-col items-center max-w-4xl mx-auto py-12 px-4">
      <div className="w-full text-center mb-12">
        <h1 className="text-4xl md:text-5xl font-extrabold text-gray-900 tracking-tight mb-4">
          Course Analytics
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          Identify prerequisite bottlenecks across the university catalog.
        </p>
      </div>

      <div className="w-full mb-8 flex justify-between items-center">
        <Link href="/" className="text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-2">
          &larr; Back to Search
        </Link>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-10 h-10 animate-spin text-indigo-600" />
        </div>
      ) : error ? (
        <div className="w-full p-4 bg-red-50 text-red-700 rounded-xl border border-red-100">
          {error}
        </div>
      ) : (
        <div className="w-full bg-white rounded-2xl shadow-sm border overflow-hidden">
          <div className="px-6 py-5 border-b border-gray-100 bg-gray-50">
            <h3 className="text-lg font-bold text-gray-900">Top Prerequisite Bottlenecks</h3>
            <p className="text-sm text-gray-500">Courses most frequently required by other courses</p>
          </div>
          <ul className="divide-y divide-gray-100">
            {bottlenecks.map((course, idx) => (
              <li key={course.course_id} className="p-6 hover:bg-gray-50 transition-colors flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-full bg-indigo-100 text-indigo-700 font-bold text-sm">
                    {idx + 1}
                  </div>
                  <div>
                    <h4 className="text-md font-bold text-gray-900">{course.course_id}</h4>
                    <p className="text-sm text-gray-600">{course.title}</p>
                  </div>
                </div>
                <div className="flex flex-col items-end">
                  <span className="text-2xl font-black text-gray-900">{course.dependency_count}</span>
                  <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Dependencies</span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
