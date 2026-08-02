'use client';

import { Finding } from '@/types/matilda';
import { restoreContextAction } from '@/lib/api/documents';
import { useState } from 'react';

interface Props {
  finding: Finding | null;
  isOpen: boolean;
  onClose: () => void;
  onApplyRevision?: (findingId: string, text: string) => void;
}

export default function RestoreContextModal({ finding, isOpen, onClose, onApplyRevision }: Props) {
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

  if (!isOpen || !finding || !finding.suggestedRevision) return null;

  const { originalText, suggestedText, evidenceUsed, rationale } = finding.suggestedRevision;

  const handleAction = async (decision: 'ACCEPT' | 'KEEP') => {
    const res = await restoreContextAction(finding.documentId, finding.id, decision);
    setFeedbackMsg(res.message);

    if (decision === 'ACCEPT' && onApplyRevision) {
      onApplyRevision(finding.id, suggestedText);
    }

    setTimeout(() => {
      setFeedbackMsg(null);
      onClose();
    }, 1200);
  };

  return (
    <div className="fixed inset-0 z-50 bg-[#1C1917]/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-[#FAF8F5] border border-[#E7E2D8] max-w-4xl w-full rounded-sm shadow-paper-lg overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="bg-white border-b border-[#E7E2D8] px-6 py-4 flex items-center justify-between">
          <div>
            <span className="text-[10px] font-bold text-[#B91C1C] uppercase tracking-wider block">
              RESTORE HISTORICAL CONTEXT
            </span>
            <h2 className="font-serif text-xl font-bold text-[#1C1917]">
              {finding.title}
            </h2>
          </div>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="text-[#737373] hover:text-[#1C1917] text-lg font-bold px-2 py-1"
          >
            ✕
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs">
          {feedbackMsg && (
            <div className="p-3 bg-[#FEF2F2] border border-[#FCA5A5] text-[#991B1B] font-semibold text-center rounded-sm">
              {feedbackMsg}
            </div>
          )}

          {/* Rationale */}
          <div className="bg-white border border-[#E7E2D8] p-4 rounded-sm">
            <p className="text-[10px] font-bold text-[#737373] uppercase tracking-wider mb-1">
              HISTORICAL ATTRIBUTION RATIONALE
            </p>
            <p className="font-sans text-xs text-[#1C1917] leading-relaxed">
              {rationale}
            </p>
          </div>

          {/* Comparison Split View */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Original */}
            <div className="bg-white border border-[#E7E2D8] rounded-sm p-4 space-y-2">
              <span className="text-[10px] font-bold text-[#737373] uppercase tracking-wider block border-b border-[#E7E2D8] pb-1">
                ORIGINAL MANUSCRIPT PASSAGE
              </span>
              <p className="font-serif text-sm text-[#4A463D] leading-relaxed">
                &ldquo;{originalText}&rdquo;
              </p>
            </div>

            {/* Matilda Suggestion */}
            <div className="bg-[#FEF2F2] border border-[#FCA5A5] rounded-sm p-4 space-y-2">
              <span className="text-[10px] font-bold text-[#B91C1C] uppercase tracking-wider block border-b border-[#FCA5A5] pb-1">
                MATILDA SUGGESTED REVISION
              </span>
              <p className="font-serif text-sm text-[#1C1917] leading-relaxed">
                &ldquo;{suggestedText}&rdquo;
              </p>
            </div>
          </div>

          {/* Evidence Used */}
          <div className="space-y-2">
            <p className="text-[10px] font-bold text-[#737373] uppercase tracking-wider">
              EVIDENCE SOURCES USED FOR REVISION
            </p>
            <div className="grid grid-cols-1 gap-2">
              {evidenceUsed.map((ev, i) => (
                <div key={ev.id || i} className="bg-white border border-[#E7E2D8] p-3 rounded-sm">
                  <p className="font-bold text-xs text-[#1C1917]">{ev.title}</p>
                  <p className="text-[10px] text-[#737373]">{ev.source}</p>
                  <p className="font-serif text-xs text-[#4A463D] italic mt-1">&ldquo;{ev.excerpt}&rdquo;</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Modal Footer / Actions */}
        <div className="bg-white border-t border-[#E7E2D8] px-6 py-4 flex items-center justify-between">
          <p className="text-[10px] text-[#737373] italic">
            Note: This is a UI workflow demonstration. Document text in persistent storage is not modified.
          </p>
          <div className="flex items-center gap-3">
            <button
              onClick={() => handleAction('KEEP')}
              className="px-4 py-2 border border-[#D6CFBF] bg-white hover:bg-[#FAF8F5] text-[#1C1917] text-xs font-bold uppercase tracking-wider rounded-sm transition-colors"
            >
              KEEP ORIGINAL
            </button>
            <button
              onClick={() => handleAction('ACCEPT')}
              className="px-5 py-2 bg-[#B91C1C] hover:bg-[#991B1B] text-white text-xs font-bold uppercase tracking-wider rounded-sm shadow-paper transition-colors"
            >
              ACCEPT REVISION
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
