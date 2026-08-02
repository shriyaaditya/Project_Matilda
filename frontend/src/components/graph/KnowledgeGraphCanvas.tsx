'use client';

import { KnowledgeGraphData, GraphNode } from '@/types/matilda';
import { useState, useMemo } from 'react';

interface Props {
  data: KnowledgeGraphData;
  selectedNodeId: string | null;
  onSelectNode: (node: GraphNode) => void;
}

export default function KnowledgeGraphCanvas({ data, selectedNodeId, onSelectNode }: Props) {
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  // Compute 2D node layout positions deterministically for demo canvas
  const nodePositions = useMemo(() => {
    const positions: Record<string, { x: number; y: number }> = {};
    const total = data.nodes.length;
    const width = 800;
    const height = 500;
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = 180;

    data.nodes.forEach((node, i) => {
      // Special center nodes
      if (node.id === 'node-rf') {
        positions[node.id] = { x: centerX - 80, y: centerY - 20 };
      } else if (node.id === 'node-p51') {
        positions[node.id] = { x: centerX + 60, y: centerY };
      } else {
        const angle = ((i - 2) / (total - 2)) * 2 * Math.PI;
        positions[node.id] = {
          x: centerX + Math.cos(angle) * (radius + (i % 2 === 0 ? 40 : -30)),
          y: centerY + Math.sin(angle) * (radius + (i % 2 === 0 ? 30 : -40)),
        };
      }
    });

    return positions;
  }, [data.nodes]);

  const getNodeColor = (type: string) => {
    switch (type) {
      case 'Person':
        return { bg: '#B91C1C', text: '#FFFFFF', border: '#991B1B' };
      case 'Institution':
        return { bg: '#1C1917', text: '#FFFFFF', border: '#4A463D' };
      case 'Artifact':
        return { bg: '#D97706', text: '#FFFFFF', border: '#B45309' };
      case 'Publication':
        return { bg: '#2563EB', text: '#FFFFFF', border: '#1D4ED8' };
      default:
        return { bg: '#4B5563', text: '#FFFFFF', border: '#374151' };
    }
  };

  return (
    <div className="flex-1 bg-[#FAF8F5] relative overflow-hidden flex items-center justify-center p-4">
      {/* Background Grid Pattern */}
      <div
        className="absolute inset-0 opacity-20 pointer-events-none"
        style={{
          backgroundImage: 'radial-gradient(#1C1917 0.75px, transparent 0.75px)',
          backgroundSize: '24px 24px',
        }}
      />

      {/* SVG Canvas for Edges & Nodes */}
      <svg
        viewBox="0 0 800 500"
        className="w-full h-full max-w-[1000px] max-h-[650px] relative z-10"
      >
        <defs>
          <marker
            id="arrowhead"
            markerWidth="8"
            markerHeight="6"
            refX="18"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 8 3, 0 6" fill="#A8A29E" />
          </marker>
        </defs>

        {/* Render Edges */}
        {data.edges.map((edge) => {
          const sourcePos = nodePositions[edge.source];
          const targetPos = nodePositions[edge.target];
          if (!sourcePos || !targetPos) return null;

          const isHighlighted =
            hoveredNodeId === edge.source ||
            hoveredNodeId === edge.target ||
            selectedNodeId === edge.source ||
            selectedNodeId === edge.target;

          const midX = (sourcePos.x + targetPos.x) / 2;
          const midY = (sourcePos.y + targetPos.y) / 2;

          return (
            <g key={edge.id}>
              <line
                x1={sourcePos.x}
                y1={sourcePos.y}
                x2={targetPos.x}
                y2={targetPos.y}
                stroke={isHighlighted ? '#1C1917' : '#D6CFBF'}
                strokeWidth={isHighlighted ? 2.5 : 1}
                strokeDasharray={edge.type === 'ASSOCIATED_WITH' ? '4 4' : undefined}
                markerEnd="url(#arrowhead)"
              />
              <text
                x={midX}
                y={midY - 4}
                textAnchor="middle"
                className="text-[9px] font-mono font-medium fill-[#737373] pointer-events-none"
                style={{ backgroundColor: '#FAF8F5' }}
              >
                {edge.label}
              </text>
            </g>
          );
        })}

        {/* Render Nodes */}
        {data.nodes.map((node) => {
          const pos = nodePositions[node.id] || { x: 400, y: 250 };
          const isSelected = selectedNodeId === node.id;
          const isHovered = hoveredNodeId === node.id;
          const style = getNodeColor(node.type);

          return (
            <g
              key={node.id}
              transform={`translate(${pos.x}, ${pos.y})`}
              onClick={() => onSelectNode(node)}
              onMouseEnter={() => setHoveredNodeId(node.id)}
              onMouseLeave={() => setHoveredNodeId(null)}
              className="cursor-pointer transition-all duration-150"
            >
              {/* Pulse Ring if selected */}
              {(isSelected || isHovered) && (
                <circle
                  r={28}
                  fill="none"
                  stroke={style.bg}
                  strokeWidth="2"
                  strokeOpacity="0.4"
                  className="animate-ping"
                />
              )}

              {/* Main Node Circle */}
              <circle
                r={20}
                fill={style.bg}
                stroke={isSelected ? '#1C1917' : style.border}
                strokeWidth={isSelected ? 3 : 1.5}
                className="shadow-paper hover:scale-110 transition-transform"
              />

              {/* Node Icon / Initial */}
              <text
                textAnchor="middle"
                dy="4"
                fill={style.text}
                className="text-xs font-bold font-sans pointer-events-none"
              >
                {node.label.charAt(0)}
              </text>

              {/* Node Label Card */}
              <g transform="translate(0, 32)">
                <rect
                  x="-65"
                  y="-10"
                  width="130"
                  height="22"
                  rx="3"
                  fill="#FFFFFF"
                  stroke={isSelected ? '#1C1917' : '#E7E2D8'}
                  strokeWidth={isSelected ? 1.5 : 1}
                />
                <text
                  textAnchor="middle"
                  dy="4"
                  fill="#1C1917"
                  className="text-[10px] font-semibold font-sans pointer-events-none"
                >
                  {node.label.length > 18 ? node.label.substring(0, 16) + '...' : node.label}
                </text>
              </g>
            </g>
          );
        })}
      </svg>

      {/* Legend overlay */}
      <div className="absolute bottom-4 left-4 bg-white/90 backdrop-blur-xs border border-[#E7E2D8] p-3 rounded-sm text-[10px] space-y-1.5 z-20">
        <span className="font-bold text-[#737373] uppercase tracking-wider block">Legend</span>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-[#B91C1C]" />
          <span className="text-[#1C1917]">Person</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-[#1C1917]" />
          <span className="text-[#1C1917]">Institution</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-[#D97706]" />
          <span className="text-[#1C1917]">Artifact</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-[#2563EB]" />
          <span className="text-[#1C1917]">Publication / Doc</span>
        </div>
      </div>
    </div>
  );
}
