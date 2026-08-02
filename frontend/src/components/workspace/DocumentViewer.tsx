'use client';

import { Document, DocumentPage, Finding } from '@/types/matilda';
import React, { useEffect, useRef } from 'react';

interface Props {
  documentData: Document;
  findings: Finding[];
  selectedFindingId: string | null;
  onSelectFinding: (findingId: string) => void;
  activePage: number;
  onPageChange: (page: number) => void;
}

export default function DocumentViewer({
  documentData,
  findings,
  selectedFindingId,
  onSelectFinding,
  activePage,
  onPageChange,
}: Props) {
  const currentPageData: DocumentPage | undefined = documentData.pages.find(
    (p) => p.pageNumber === activePage
  );

  const containerRef = useRef<HTMLDivElement>(null);

  // Scroll active finding into view when selected
  useEffect(() => {
    if (selectedFindingId && typeof window !== 'undefined') {
      const selectedEl = window.document.getElementById(`finding-annotation-${selectedFindingId}`);
      if (selectedEl) {
        selectedEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [selectedFindingId]);

  // Helper to render paragraph with inline annotations
  const renderAnnotatedText = (
    text: string,
    annotations?: { findingId: string; highlightText: string }[]
  ) => {
    if (!annotations || annotations.length === 0) {
      return text;
    }

    // Sort annotations by index in text
    let elements: React.ReactNode[] = [];
    let lastIdx = 0;

    // Find matches
    const matches: { start: number; end: number; findingId: string; text: string }[] = [];

    annotations.forEach((ann) => {
      const start = text.indexOf(ann.highlightText);
      if (start !== -1) {
        matches.push({
          start,
          end: start + ann.highlightText.length,
          findingId: ann.findingId,
          text: ann.highlightText,
        });
      }
    });

    matches.sort((a, b) => a.start - b.start);

    matches.forEach((m, idx) => {
      if (m.start > lastIdx) {
        elements.push(text.substring(lastIdx, m.start));
      }

      const isSelected = selectedFindingId === m.findingId;

      elements.push(
        <span
          key={`ann-${m.findingId}-${idx}`}
          id={`finding-annotation-${m.findingId}`}
          onClick={() => onSelectFinding(m.findingId)}
          className={`annotation-highlight ${isSelected ? 'active' : ''}`}
          title="Click to view Matilda finding & evidence"
        >
          {m.text}
        </span>
      );

      lastIdx = m.end;
    });

    if (lastIdx < text.length) {
      elements.push(text.substring(lastIdx));
    }

    return elements;
  };

  return (
    <main
      ref={containerRef}
      className="flex-1 bg-[#FAF8F5] overflow-y-auto h-full p-4 sm:p-8 md:p-12 flex flex-col items-center"
    >
      {/* Page Header / Pagination Controls */}
      <div className="w-full max-w-3xl flex items-center justify-between mb-6 text-xs text-[#737373] font-mono border-b border-[#E7E2D8] pb-3 shrink-0">
        <div>
          <span>DOCUMENT MANUSCRIPT</span>
          {currentPageData?.title && (
            <span className="ml-3 text-[#1C1917] font-serif font-semibold">
              {currentPageData.title}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <button
            disabled={activePage <= 1}
            onClick={() => onPageChange(activePage - 1)}
            className="px-2 py-1 bg-white border border-[#D6CFBF] hover:bg-[#FAF8F5] disabled:opacity-40 disabled:cursor-not-allowed rounded-sm text-[#1C1917]"
          >
            ← Prev Page
          </button>
          <span className="font-bold text-[#1C1917]">
            Page {activePage} of {documentData.pages.length}
          </span>
          <button
            disabled={activePage >= documentData.pages.length}
            onClick={() => onPageChange(activePage + 1)}
            className="px-2 py-1 bg-white border border-[#D6CFBF] hover:bg-[#FAF8F5] disabled:opacity-40 disabled:cursor-not-allowed rounded-sm text-[#1C1917]"
          >
            Next Page →
          </button>
        </div>
      </div>

      {/* Academic Paper Book Page */}
      <div className="w-full max-w-3xl bg-white border border-[#E7E2D8] rounded-sm p-8 sm:p-14 shadow-paper space-y-8 min-h-[850px] flex flex-col justify-between">
        <div className="space-y-8">
          {/* Document Title Header */}
          {activePage === 1 && (
            <div className="border-b border-[#E7E2D8] pb-8 text-center space-y-4">
              <span className="text-[10px] font-bold uppercase tracking-widest text-[#737373] block">
                Primary Scholarly Source
              </span>
              <h1 className="font-serif text-3xl sm:text-4xl font-bold text-[#1C1917] tracking-tight leading-tight">
                {documentData.title}
              </h1>
              {documentData.subtitle && (
                <p className="font-serif text-base text-[#4A463D] italic">
                  {documentData.subtitle}
                </p>
              )}
              {documentData.author && (
                <p className="text-xs font-sans text-[#737373] tracking-wide font-medium">
                  By {documentData.author}
                </p>
              )}
            </div>
          )}

          {/* Chapter Title if present */}
          {currentPageData?.title && activePage > 1 && (
            <h2 className="font-serif text-2xl font-bold text-[#1C1917] border-b border-[#E7E2D8] pb-3">
              {currentPageData.title}
            </h2>
          )}

          {/* Long-form Serif Body Text */}
          <div className="space-y-6">
            {currentPageData?.paragraphs.map((p) => (
              <p
                key={p.id}
                className="font-serif text-base sm:text-lg text-[#1C1917] leading-relaxed tracking-normal"
              >
                {renderAnnotatedText(p.text, p.annotations)}
              </p>
            ))}
          </div>

          {/* Optional Document Image placeholder */}
          {currentPageData?.imageUrl && (
            <div className="my-6 border border-[#E7E2D8] p-4 bg-[#FAF8F5] text-center rounded-sm space-y-2">
              <div className="w-full h-48 bg-[#E7E2D8] flex items-center justify-center font-serif text-sm text-[#737373] italic">
                [ Primary Source Archival Plate / Photograph ]
              </div>
              <p className="text-xs text-[#737373] italic font-serif">
                Figure {activePage}.1 — Historical X-ray diffraction plate archival image
              </p>
            </div>
          )}
        </div>

        {/* Page Footer */}
        <div className="pt-8 border-t border-[#E7E2D8] flex items-center justify-between text-xs text-[#737373] font-serif">
          <span>Project Matilda — Scholarly Research View</span>
          <span>Page {activePage}</span>
        </div>
      </div>
    </main>
  );
}
