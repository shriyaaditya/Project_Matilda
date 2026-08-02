'use client';

import { GraphNode } from '@/types/matilda';

interface Props {
  node: GraphNode | null;
  onClose: () => void;
}

export default function EntityDetailPanel({ node, onClose }: Props) {
  if (!node) return null;

  return (
    <aside className="w-full md:w-96 bg-[#FAF8F5] border-l border-[#E7E2D8] h-full flex flex-col overflow-y-auto p-6 space-y-6 shadow-paper-lg z-30">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-[#E7E2D8] pb-4">
        <div>
          <span className="text-[10px] font-bold text-[#B91C1C] uppercase tracking-widest block mb-1">
            {node.type} ENTITY
          </span>
          <h2 className="font-serif text-2xl font-bold text-[#1C1917] leading-tight">
            {node.label}
          </h2>
          {node.subtitle && (
            <p className="text-xs text-[#737373] mt-1 font-medium">{node.subtitle}</p>
          )}
        </div>
        <button
          onClick={onClose}
          aria-label="Close entity detail panel"
          className="text-[#737373] hover:text-[#1C1917] font-bold text-lg p-1"
        >
          ✕
        </button>
      </div>

      {/* Affiliation */}
      {node.affiliation && (
        <div className="bg-white border border-[#E7E2D8] p-3 rounded-sm text-xs">
          <span className="text-[10px] font-bold text-[#737373] uppercase tracking-wider block mb-0.5">
            Primary Affiliation
          </span>
          <p className="font-semibold text-[#1C1917]">{node.affiliation}</p>
        </div>
      )}

      {/* Description */}
      {node.description && (
        <div className="space-y-1 text-xs">
          <span className="text-[10px] font-bold text-[#737373] uppercase tracking-wider block">
            Historical Overview
          </span>
          <p className="font-sans text-[#4A463D] leading-relaxed bg-white border border-[#E7E2D8] p-3 rounded-sm">
            {node.description}
          </p>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3 text-xs">
        <div className="bg-white border border-[#E7E2D8] p-3 rounded-sm text-center">
          <span className="text-[10px] font-bold text-[#737373] uppercase tracking-wider block">
            Documents
          </span>
          <span className="font-serif text-xl font-bold text-[#1C1917]">
            {node.documentsCount || 0}
          </span>
        </div>
        <div className="bg-white border border-[#E7E2D8] p-3 rounded-sm text-center">
          <span className="text-[10px] font-bold text-[#737373] uppercase tracking-wider block">
            Evidence Items
          </span>
          <span className="font-serif text-xl font-bold text-[#1C1917]">
            {node.evidenceCount || 0}
          </span>
        </div>
      </div>

      {/* Demo data badge */}
      {node.isDemoData && (
        <div className="bg-[#FEF2F2] border border-[#FCA5A5] p-3 rounded-sm text-[10px] text-[#991B1B] space-y-1">
          <span className="font-bold uppercase tracking-wider block">Demo Graph Node</span>
          <p className="leading-tight">
            This graph node is supplied via the isolated demo fixture. In production, entity relationships are fetched dynamically from the Matilda Graph API.
          </p>
        </div>
      )}
    </aside>
  );
}
