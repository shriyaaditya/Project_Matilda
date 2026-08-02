'use client';

import { Document, Finding, FindingCategory } from '@/types/matilda';

interface Props {
  document: Document;
  findings: Finding[];
  selectedFindingId: string | null;
  onSelectFinding: (findingId: string) => void;
  activeCategoryFilter: string | null;
  onSelectCategoryFilter: (cat: string | null) => void;
}

const CATEGORY_LABELS: Record<FindingCategory, string> = {
  credit_displacement: 'Credit displacement',
  missing_attribution: 'Missing attribution',
  context_omission: 'Context omission',
  representation_gap: 'Representation gap',
  unsupported_claim: 'Unsupported claim',
};

export default function DocumentSidebar({
  document,
  findings,
  selectedFindingId,
  onSelectFinding,
  activeCategoryFilter,
  onSelectCategoryFilter,
}: Props) {
  // Count findings per category
  const categoryCounts = (Object.keys(CATEGORY_LABELS) as FindingCategory[]).reduce(
    (acc, cat) => {
      acc[cat] = findings.filter((f) => f.category === cat).length;
      return acc;
    },
    {} as Record<FindingCategory, number>
  );

  return (
    <aside className="w-full lg:w-80 bg-[#FAF8F5] border-r border-[#E7E2D8] h-full flex flex-col overflow-y-auto text-xs p-5 space-y-6">
      {/* PROJECT / DOCUMENT HEADER */}
      <div className="space-y-2 border-b border-[#E7E2D8] pb-4">
        <span className="text-[10px] font-bold text-[#737373] uppercase tracking-widest block">
          PROJECT / DOCUMENT
        </span>
        <h2 className="font-serif text-base font-bold text-[#1C1917] leading-snug">
          {document.title}
        </h2>
        {document.subtitle && (
          <p className="text-[11px] text-[#737373] leading-normal">{document.subtitle}</p>
        )}
        <div className="pt-1 flex items-center justify-between text-[10px] font-mono text-[#737373]">
          <span>Type: {document.fileType}</span>
          <span>{document.uploadDate}</span>
        </div>
      </div>

      {/* ANALYSIS TYPE */}
      <div className="space-y-1 bg-white border border-[#E7E2D8] p-3 rounded-sm">
        <span className="text-[10px] font-bold text-[#737373] uppercase tracking-wider block">
          ANALYSIS TYPE
        </span>
        <p className="font-semibold text-xs text-[#1C1917]">{document.analysisType}</p>
      </div>

      {/* HISTORICAL CONTEXT COVERAGE METRIC */}
      {document.historicalContextCoverage && (
        <div className="bg-white border border-[#E7E2D8] p-3 rounded-sm space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#737373] uppercase tracking-wider">
              HISTORICAL CONTEXT COVERAGE
            </span>
            <span className="text-[9px] font-bold text-[#B91C1C] uppercase tracking-widest bg-[#FEF2F2] px-1.5 py-0.5 rounded border border-[#FCA5A5]">
              DEMO DATA
            </span>
          </div>
          <p className="font-serif text-2xl font-bold text-[#1C1917]">
            {document.historicalContextCoverage.scoreDisplay}
          </p>
          <p className="text-[10px] text-[#737373] leading-tight">
            {document.historicalContextCoverage.note}
          </p>
        </div>
      )}

      {/* FINDINGS LIST BY CATEGORY */}
      <div className="space-y-3">
        <div className="flex items-center justify-between border-b border-[#E7E2D8] pb-1">
          <span className="text-[10px] font-bold text-[#1C1917] uppercase tracking-widest">
            FINDINGS ({findings.length})
          </span>
          {activeCategoryFilter && (
            <button
              onClick={() => onSelectCategoryFilter(null)}
              className="text-[10px] text-[#B91C1C] hover:underline uppercase font-bold"
            >
              Clear Filter
            </button>
          )}
        </div>

        <div className="space-y-1">
          {(Object.keys(CATEGORY_LABELS) as FindingCategory[]).map((cat) => {
            const count = categoryCounts[cat];
            const isFilterActive = activeCategoryFilter === cat;
            return (
              <div key={cat} className="space-y-1">
                <button
                  onClick={() => onSelectCategoryFilter(isFilterActive ? null : cat)}
                  className={`w-full text-left px-2.5 py-1.5 rounded-sm flex items-center justify-between transition-colors ${
                    isFilterActive
                      ? 'bg-[#FEF2F2] text-[#991B1B] font-bold border border-[#FCA5A5]'
                      : 'hover:bg-white text-[#1C1917] font-medium'
                  }`}
                >
                  <span className="text-xs">{CATEGORY_LABELS[cat]}</span>
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-mono ${
                      count > 0 ? 'bg-[#E7E2D8] text-[#1C1917]' : 'text-[#737373]'
                    }`}
                  >
                    {count}
                  </span>
                </button>
              </div>
            );
          })}
        </div>

        {/* List of individual findings filtered */}
        <div className="pt-2 space-y-2">
          {findings
            .filter((f) => !activeCategoryFilter || f.category === activeCategoryFilter)
            .map((f) => {
              const isSelected = selectedFindingId === f.id;
              return (
                <button
                  key={f.id}
                  onClick={() => onSelectFinding(f.id)}
                  className={`w-full text-left p-2.5 rounded-sm border transition-all ${
                    isSelected
                      ? 'bg-white border-[#B91C1C] shadow-paper text-[#1C1917]'
                      : 'bg-white/60 border-[#E7E2D8] hover:border-[#D6CFBF] text-[#4A463D]'
                  }`}
                >
                  <div className="flex items-start justify-between gap-1 mb-1">
                    <span className="text-[9px] font-bold uppercase tracking-wider text-[#B91C1C]">
                      P.{f.page} • {CATEGORY_LABELS[f.category]}
                    </span>
                    <span className="text-[9px] font-mono text-[#737373]">
                      {f.status}
                    </span>
                  </div>
                  <p className="font-semibold text-xs text-[#1C1917] line-clamp-2 leading-snug">
                    {f.title}
                  </p>
                </button>
              );
            })}
        </div>
      </div>

      {/* DOCUMENT METADATA INDEX */}
      <div className="space-y-3 pt-2 border-t border-[#E7E2D8]">
        <span className="text-[10px] font-bold text-[#1C1917] uppercase tracking-widest block">
          DOCUMENT INDEX
        </span>

        <details className="group bg-white border border-[#E7E2D8] rounded-sm p-2 text-xs">
          <summary className="cursor-pointer font-semibold text-[#1C1917] flex justify-between items-center">
            <span>People ({document.metadata.peopleCount})</span>
            <span className="text-[10px] text-[#737373]">▼</span>
          </summary>
          <ul className="mt-2 space-y-1 pl-2 text-[11px] text-[#4A463D] border-t border-[#E7E2D8] pt-2">
            {document.metadata.peopleList.map((p) => (
              <li key={p}>• {p}</li>
            ))}
          </ul>
        </details>

        <details className="group bg-white border border-[#E7E2D8] rounded-sm p-2 text-xs">
          <summary className="cursor-pointer font-semibold text-[#1C1917] flex justify-between items-center">
            <span>Claims ({document.metadata.claimsCount})</span>
            <span className="text-[10px] text-[#737373]">▼</span>
          </summary>
          <ul className="mt-2 space-y-1 pl-2 text-[11px] text-[#4A463D] border-t border-[#E7E2D8] pt-2">
            {document.metadata.claimsList.map((c) => (
              <li key={c}>• {c}</li>
            ))}
          </ul>
        </details>

        <details className="group bg-white border border-[#E7E2D8] rounded-sm p-2 text-xs">
          <summary className="cursor-pointer font-semibold text-[#1C1917] flex justify-between items-center">
            <span>Sources ({document.metadata.sourcesCount})</span>
            <span className="text-[10px] text-[#737373]">▼</span>
          </summary>
          <ul className="mt-2 space-y-1 pl-2 text-[11px] text-[#4A463D] border-t border-[#E7E2D8] pt-2">
            {document.metadata.sourcesList.map((s) => (
              <li key={s}>• {s}</li>
            ))}
          </ul>
        </details>
      </div>
    </aside>
  );
}
