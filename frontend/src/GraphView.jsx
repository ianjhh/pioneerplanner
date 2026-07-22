import { useState, useEffect, useCallback } from 'react'
import ReactFlow, { Background, Controls, applyNodeChanges, applyEdgeChanges, MarkerType } from 'reactflow'
import 'reactflow/dist/style.css'
import dagre from 'dagre'

const dagreGraph = new dagre.graphlib.Graph()
dagreGraph.setDefaultEdgeLabel(() => ({}))

const getLayoutedElements = (nodes, edges, direction = 'TB') => {
  dagreGraph.setGraph({ rankdir: direction })

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 150, height: 50 })
  })

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target)
  })

  dagre.layout(dagreGraph)

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id)
    node.targetPosition = 'top'
    node.sourcePosition = 'bottom'
    node.position = {
      x: nodeWithPosition.x - 75,
      y: nodeWithPosition.y - 25,
    }
    return node
  })

  return { nodes, edges }
}

export default function GraphView({ courseId }) {
  const [nodes, setNodes] = useState([])
  const [edges, setEdges] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchGraph = async () => {
    if (!courseId) return
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch(`http://localhost:8000/api/v1/courses/${courseId}/prereq-path`)
      if (!response.ok) throw new Error('Failed to fetch prerequisite path')
      const data = await response.json()
      
      const initialNodes = []
      const initialEdges = []
      
      const buildElements = (node, parentId = null) => {
        initialNodes.push({
          id: node.course_id,
          data: { label: `${node.course_id}\n${node.title || ''}` },
          style: { border: '1px solid #777', padding: 10, borderRadius: 5, background: '#fff' }
        })
        
        if (parentId) {
          initialEdges.push({
            id: `${node.course_id}-${parentId}`,
            source: node.course_id,
            target: parentId,
            animated: true,
            label: node.logic_type || 'REQ',
            markerEnd: { type: MarkerType.ArrowClosed }
          })
        }
        
        if (node.prerequisites) {
          node.prerequisites.forEach(child => buildElements(child, node.course_id))
        }
      }
      
      buildElements(data.prerequisite_tree)
      
      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(initialNodes, initialEdges)
      setNodes(layoutedNodes)
      setEdges(layoutedEdges)
      
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchGraph()
  }, [courseId])

  const onNodesChange = useCallback((changes) => setNodes((nds) => applyNodeChanges(changes, nds)), [])
  const onEdgesChange = useCallback((changes) => setEdges((eds) => applyEdgeChanges(changes, eds)), [])

  if (!courseId) return <div className="p-4">Please search and select a course first to view its prerequisite graph.</div>
  
  return (
    <div style={{ height: '70vh', width: '100%' }}>
      {loading && <p>Loading graph...</p>}
      {error && <p className="error">{error}</p>}
      {!loading && !error && (
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          fitView
        >
          <Background color="#ccc" gap={16} />
          <Controls />
        </ReactFlow>
      )}
    </div>
  )
}
