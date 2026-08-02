'use client';

import { Finding, FindingStatus } from '@/types/matilda';

interface Props {
  findings: Finding[];
  onStatusChange: (findingId: string, status: FindingStatus) => void;
}

const STATUS_OPTIONS: FindingStatus[] = ['Open', 'Reviewed', 'Accepted', 'Dismissed'];

export default function FindingList({ findings, onStatusChange }: Props) {
  return (
    <div className="bg-white border border-[#E7E2D8] rounded-sm p-6 shadow-paper space-y-4">
      <div className="flex items-center justify-between border-b border-[#E7E2D8] pb-3">
        <h2 className="font-serif text-xl font-bold text-[#1C1917]">
          Detailed Findings & Attribution Inventory
        </h2>
        <span className="text-xs text-[#737373] font-mono">
          Showing {findings.length} findings
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-[#E7E2D8] bg-[#FAF8F5] text-[10px] font-bold text-[#737373] uppercase tracking-wider">
              <th className="p-3">Finding</th>
              <th className="p-3">Affected Passage</th>
              <th className="p-3">Related Entities</th>
              <th className="p-3">Evidence</th>
              <th className="p-3">Confidence</th>
              <th className="p-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E7E2D8]">
            {findings.map((f) => (
              <tr key={f.id} className="hover:bg-[#FAF8F5]/60 transition-colors">
                {/* Finding title & category */}
                <td className="p-3 align-top min-w-[200px]">
                  <span className="text-[9px] font-bold text-[#B91C1C] uppercase tracking-wider block mb-0.5">
                    {f.categoryTitle}
                  </span>
                  <p className="font-semibold text-xs text-[#1C1917]">{f.title}</p>
                  <p className="text-[10px] text-[#737373] mt-1 font-mono">Page {f.page}</p>
                </td>

                {/* Affected Passage */}
                <td className="p-3 align-top min-w-[240px]">
                  <p className="font-serif text-xs text-[#4A463D] italic line-clamp-3">
                    &ldquo;{f.passage}&rdquo;
                  </p>
                </td>

                {/* Related Entities */}
                <td className="p-3 align-top min-w-[140px]">
                  <div className="space-y-1">
                    {f.relatedEntities.map((ent) => (
                      <span
                        key={ent.id}
                        className="inline-block text-[10px] bg-[#FAF8F5] border border-[#E7E2D8] px-2 py-0.5 rounded-sm text-[#1C1917] font-medium mr-1"
                      >
                        {ent.name}
                      </span>
                    ))}
                  </div>
                </td>

                {/* Evidence count */}
                <td className="p-3 align-top font-mono text-center">
                  <span className="bg-[#E7E2D8] text-[#1C1917] px-2 py-0.5 rounded text-[11px] font-semibold">
                    {f.evidence.length} sources
                  </span>
                </td>

                {/* Confidence */}
                <td className="p-3 align-top font-mono">
                  {f.confidence !== undefined ? (
                    <span className="text-[11px] text-[#1C1917] font-bold">
                      {(f.confidence * 100).toFixed(0)}%
                    </span>
                  ) : (
                    <span className="text-[10px] text-[#737373] italic">N/A</span>
                  )}
                </td>

                {/* Status Toggle */}
                <td className="p-3 align-top">
                  <select
                    value={f.status}
                    onChange={(e) => onStatusChange(f.id, e.target.value as FindingStatus)}
                    className={`text-[10px] font-bold py-1 px-2 rounded-sm border focus:outline-none ${
                      f.status === 'Accepted'
                        ? 'bg-[#FEF2F2] border-[#FCA5A5] text-[#991B1B]'
                        : f.status === 'Reviewed'
                        ? 'bg-[#EFF6FF] border-[#BFDBFE] text-[#1E40AF]'
                        : f.status === 'Dismissed'
                        ? 'bg-[#F3F4F6] border-[#D1D5DB] text-[#4B5563]'
                        : 'bg-white border-[#D6CFBF] text-[#1C1917]'
                    }`}
                  >
                    {STATUS_OPTIONS.map((st) => (
                      <option key={st} value={st}>
                        {st}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
