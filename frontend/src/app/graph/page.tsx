"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Search, AlertCircle, Loader2 } from "lucide-react";
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  MarkerType,
  Position
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "dagre";
import { PrereqPathResponse, PrereqTreeNode } from "@/types/api";

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = "TB") => {
  const isHorizontal = direction === "LR";
  dagreGraph.setGraph({ rankdir: direction });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 250, height: 100 });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const newNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      targetPosition: isHorizontal ? Position.Left : Position.Top,
      sourcePosition: isHorizontal ? Position.Right : Position.Bottom,
      position: {
        x: nodeWithPosition.x - 250 / 2,
        y: nodeWithPosition.y - 100 / 2,
      },
    } as Node;
  });

  return { nodes: newNodes, edges };
};

function GraphComponent() {
  const searchParams = useSearchParams();
  const initialCourse = searchParams.get("course") || "";
  
  const [targetCourse, setTargetCourse] = useState(initialCourse);
  const [searchInput, setSearchInput] = useState(initialCourse);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  useEffect(() => {
    if (targetCourse) {
      fetchGraphData(targetCourse);
    }
  }, [targetCourse]);

  const fetchGraphData = async (courseId: string) => {
    setLoading(true);
    setError("");
    
    try {
      const res = await fetch(`http://localhost:8000/api/v1/courses/${encodeURIComponent(courseId)}/prereq-path`);
      if (res.status === 404) {
        throw new Error("Course not found in catalog.");
      }
      if (!res.ok) throw new Error("Failed to fetch prerequisite data.");
      
      const data: PrereqPathResponse = await res.json();
      buildGraph(data.prerequisite_tree);
    } catch (err: any) {
      setError(err.message || "An error occurred");
      setNodes([]);
      setEdges([]);
    } finally {
      setLoading(false);
    }
  };

  const buildGraph = (root: PrereqTreeNode) => {
    const newNodes: Node[] = [];
    const newEdges: Edge[] = [];

    const traverse = (node: PrereqTreeNode, parentId: string | null = null, relationshipType: string | null = null) => {
      // Create Node
      const isRoot = parentId === null;
      newNodes.push({
        id: node.course_id,
        position: { x: 0, y: 0 },
        data: { 
          label: (
            <div className="flex flex-col h-full w-full">
              <div className={`text-sm font-bold p-2 text-white rounded-t-md ${isRoot ? 'bg-indigo-600' : 'bg-slate-700'}`}>
                {node.course_id}
              </div>
              <div className="p-2 text-xs text-gray-700 bg-white border-b border-l border-r border-gray-200 rounded-b-md flex-grow">
                {node.title ? <p className="truncate font-medium" title={node.title}>{node.title}</p> : <p className="italic text-gray-400">Unknown Title</p>}
                {node.units && <p className="text-gray-500 mt-1">{node.units} Units</p>}
                {node.minimum_grade && <p className="text-emerald-600 mt-1 font-semibold">Min: {node.minimum_grade}</p>}
              </div>
            </div>
          ) 
        },
        style: { 
          width: 250, 
          padding: 0, 
          border: 'none',
          borderRadius: '6px',
          boxShadow: isRoot ? '0 4px 6px -1px rgba(79, 70, 229, 0.3)' : '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
        },
      });

      // Create Edge to Parent
      if (parentId) {
        let edgeColor = '#94a3b8';
        let edgeLabel = '';
        if (relationshipType === 'OR') {
          edgeColor = '#f59e0b'; // amber
          edgeLabel = 'OR';
        } else if (relationshipType === 'AND') {
          edgeColor = '#3b82f6'; // blue
          edgeLabel = 'AND';
        }

        newEdges.push({
          id: `e-${node.course_id}-${parentId}`,
          source: node.course_id,
          target: parentId,
          animated: true,
          label: edgeLabel,
          style: { stroke: edgeColor, strokeWidth: 2 },
          labelStyle: { fill: edgeColor, fontWeight: 700 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: edgeColor,
          },
        });
      }

      // Recursively traverse children
      if (node.prerequisites && node.prerequisites.length > 0) {
        node.prerequisites.forEach(prereq => {
          traverse(prereq, node.course_id, prereq.logic_type || 'AND');
        });
      }
    };

    traverse(root);
    
    const layouted = getLayoutedElements(newNodes, newEdges);
    setNodes(layouted.nodes);
    setEdges(layouted.edges);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      {/* Header / Search Bar */}
      <div className="p-4 border-b border-gray-100 bg-gray-50/50 flex flex-col sm:flex-row gap-4 justify-between items-center z-10">
        <div>
          <h2 className="text-xl font-bold text-gray-800">Prerequisite Graph</h2>
          <p className="text-sm text-gray-500">Visualize dependency chains for any course</p>
        </div>
        
        <form 
          onSubmit={(e) => { e.preventDefault(); setTargetCourse(searchInput); }}
          className="flex w-full sm:w-auto"
        >
          <input
            type="text"
            className="px-4 py-2 border border-gray-300 rounded-l-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 w-full sm:w-64"
            placeholder="e.g. CS 401"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
          <button 
            type="submit" 
            className="bg-indigo-600 text-white px-4 py-2 rounded-r-lg hover:bg-indigo-700 transition-colors flex items-center justify-center min-w-[3rem]"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Search className="w-5 h-5" />}
          </button>
        </form>
      </div>

      {/* Graph Area */}
      <div className="flex-grow relative w-full h-full">
        {error ? (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-50">
            <div className="flex flex-col items-center text-red-500 max-w-md text-center p-6 bg-white rounded-xl shadow-sm border border-red-100">
              <AlertCircle className="w-12 h-12 mb-3 text-red-400" />
              <p className="font-medium text-lg">{error}</p>
              <p className="text-sm text-gray-500 mt-2">Check the course code and try again.</p>
            </div>
          </div>
        ) : !targetCourse ? (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-50 text-gray-400">
            <div className="text-center">
              <div className="bg-white p-4 rounded-full shadow-sm inline-block mb-4">
                <Search className="w-8 h-8 text-indigo-300" />
              </div>
              <p className="font-medium">Enter a course ID to view its prerequisite tree</p>
            </div>
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            attributionPosition="bottom-right"
          >
            <Controls className="bg-white shadow-md border-gray-100 rounded-lg overflow-hidden" />
            <MiniMap nodeStrokeWidth={3} className="bg-white shadow-md border-gray-100 rounded-lg" />
            <Background color="#cbd5e1" gap={20} />
          </ReactFlow>
        )}
      </div>
    </div>
  );
}

export default function GraphPage() {
  return (
    <Suspense fallback={<div className="flex justify-center items-center h-full"><Loader2 className="w-8 h-8 animate-spin text-indigo-600" /></div>}>
      <GraphComponent />
    </Suspense>
  );
}
