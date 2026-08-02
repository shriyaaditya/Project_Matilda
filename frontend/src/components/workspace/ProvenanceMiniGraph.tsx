'use client';

import { ProvenanceGraph } from '@/types/matilda';

interface Props {
  provenance: ProvenanceGraph;
}

export default function ProvenanceMiniGraph({ provenance }: Props) {
  if (!provenance || !provenance.nodes || provenance.nodes.length === 0) return null;

  return (
    <div className="bg-[#FAF8F5] border border-[#E7E2D8] rounded-sm p-4 my-3">
      <p className="text-[10px] font-bold text-[#737373] uppercase tracking-wider mb-3">
        Data & Attribution Flow Pathway
      </p>
      <div className="flex flex-col sm:flex-row items-center justify-between gap-2 relative">
        {provenance.nodes.map((node, idx) => {
          const isLast = idx === provenance.nodes.length - 1;
          return (
            <div key={node.id} className="flex flex-col sm:flex-row items-center w-full sm:w-auto">
              <div className="bg-white border border-[#D6CFBF] px-3 py-2 rounded-sm text-center shadow-paper min-w-[120px]">
                <p className="text-xs font-semibold text-[#1C1917]">{node.label}</p>
                {node.sublabel && (
                  <p className="text-[10px] text-[#737373] mt-0.5">{node.sublabel}</p>
                )}
              </div>
              {!isLast && (
                <div className="my-1 sm:my-0 sm:mx-2 text-[#737373] text-xs font-mono font-bold flex items-center justify-center">
                  <span className="hidden sm:inline">→</span>
                  <span className="sm:hidden">↓</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
