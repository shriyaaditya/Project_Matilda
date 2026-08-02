'use client';

import { Finding } from '@/types/matilda';
import ProvenanceMiniGraph from './ProvenanceMiniGraph';

interface Props {
  finding: Finding | null;
  onOpenRestoreContext: () => void;
}

export default function FindingPanel({ finding, onOpenRestoreContext }: Props) {
  if (!finding) {
    return (
      <aside className="w-full lg:w-96 bg-[#FAF8F5] border-l border-[#E7E2D8] p-6 h-full overflow-y-auto flex flex-col items-center justify-center text-center">
        <div className="w-12 h-12 rounded-full border border-[#D6CFBF] flex items-center justify-center text-[#737373] mb-3 text-lg font-serif">
          ¶
        </div>
        <h3 className="font-serif text-lg font-semibold text-[#1C1917] mb-1">
          No Finding Selected
        </h3>
        <p className="text-xs text-[#737373] max-w-xs leading-relaxed">
          Select an inline annotation underline in the document viewer or click a finding category on the left sidebar to inspect attribution & evidence.
        </p>
      </aside>
    );
  }

  return (
    <aside className="w-full lg:w-[420px] bg-[#FAF8F5] border-l border-[#E7E2D8] h-full flex flex-col overflow-hidden">
      {/* Active Header Banner */}
      <div className="bg-[#FEF2F2] border-b border-[#FCA5A5] px-6 py-3 flex items-center justify-between shrink-0">
        <span className="text-[10px] font-bold text-[#B91C1C] uppercase tracking-widest flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#B91C1C] animate-pulse" />
          ANNOTATION ACTIVE
        </span>
        {finding.confidence !== undefined && (
          <span className="text-[10px] font-mono text-[#991B1B] bg-white/80 px-2 py-0.5 rounded border border-[#FCA5A5]">
            Backend Confidence: {(finding.confidence * 100).toFixed(0)}%
          </span>
        )}
      </div>

      {/* Panel Scrollable Content */}
      <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs">
        {/* Category & Title */}
        <div>
          <span className="text-[10px] font-bold text-[#737373] uppercase tracking-wider block mb-1">
            {finding.categoryTitle}
          </span>
          <h2 className="font-serif text-xl font-bold text-[#1C1917] leading-tight">
            {finding.title}
          </h2>
        </div>

        {/* Flagged Passage Excerpt */}
        <div className="bg-white border-l-2 border-[#B91C1C] border-y border-r border-[#E7E2D8] p-3 rounded-r-sm">
          <p className="text-[10px] font-bold text-[#737373] uppercase tracking-wider mb-1">
            FLAGGED PASSAGE (PAGE {finding.page})
          </p>
          <p className="font-serif text-xs text-[#1C1917] italic leading-relaxed">
            &ldquo;{finding.passage}&rdquo;
          </p>
        </div>

        {/* Section: WHY MATILDA FLAGGED THIS */}
        <div className="space-y-2">
          <h4 className="text-[10px] font-bold text-[#1C1917] uppercase tracking-widest border-b border-[#E7E2D8] pb-1">
            WHY MATILDA FLAGGED THIS
          </h4>
          <p className="text-xs text-[#4A463D] leading-relaxed font-sans bg-white border border-[#E7E2D8] p-3 rounded-sm">
            {finding.whyFlagged}
          </p>
        </div>

        {/* Section: PROVENANCE */}
        {finding.provenance && (
          <div className="space-y-2">
            <h4 className="text-[10px] font-bold text-[#1C1917] uppercase tracking-widest border-b border-[#E7E2D8] pb-1">
              PROVENANCE
            </h4>
            <ProvenanceMiniGraph provenance={finding.provenance} />
          </div>
        )}

        {/* Section: EVIDENCE */}
        <div className="space-y-3">
          <h4 className="text-[10px] font-bold text-[#1C1917] uppercase tracking-widest border-b border-[#E7E2D8] pb-1">
            EVIDENCE & PRIMARY SOURCES ({finding.evidence.length})
          </h4>

          <div className="space-y-3">
            {finding.evidence.map((ev) => (
              <div
                key={ev.id}
                className="bg-white border border-[#E7E2D8] p-3.5 rounded-sm shadow-paper space-y-2"
              >
                <div className="flex items-start justify-between gap-2">
                  <h5 className="font-semibold text-xs text-[#1C1917] leading-snug">
                    {ev.title}
                  </h5>
                  {ev.date && (
                    <span className="text-[10px] text-[#737373] font-mono shrink-0">
                      {ev.date}
                    </span>
                  )}
                </div>

                <p className="text-[10px] text-[#737373]">
                  {ev.source} {ev.author ? `— ${ev.author}` : ''}
                </p>

                <p className="font-serif text-xs text-[#4A463D] italic bg-[#FAF8F5] p-2 border-l border-[#D6CFBF]">
                  &ldquo;{ev.excerpt}&rdquo;
                </p>

                {ev.repository && (
                  <p className="text-[9px] font-mono text-[#737373]">
                    Archive: {ev.repository}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Action Footer */}
      {finding.suggestedRevision && (
        <div className="bg-white border-t border-[#E7E2D8] p-4 shrink-0">
          <button
            onClick={onOpenRestoreContext}
            className="w-full py-3 bg-[#1C1917] hover:bg-[#4A463D] text-white text-xs font-bold uppercase tracking-widest rounded-sm shadow-paper transition-colors flex items-center justify-center gap-2"
          >
            <span>RESTORE CONTEXT</span>
            <span>→</span>
          </button>
        </div>
      )}
    </aside>
  );
}
