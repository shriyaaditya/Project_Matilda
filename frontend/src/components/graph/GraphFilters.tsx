'use client';

import { EntityType, RelationshipType } from '@/types/matilda';

interface Props {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  selectedEntityType: string;
  onEntityTypeChange: (type: string) => void;
  selectedRelType: string;
  onRelTypeChange: (rel: string) => void;
}

const ENTITY_TYPES: (EntityType | 'ALL')[] = [
  'ALL',
  'Person',
  'Institution',
  'Publication',
  'Discovery',
  'Artifact',
  'Event',
  'Document',
];

const REL_TYPES: (RelationshipType | 'ALL')[] = [
  'ALL',
  'AUTHORED',
  'WORKED_AT',
  'CONTRIBUTED_TO',
  'PRODUCED',
  'CITED_BY',
  'COLLABORATED_WITH',
  'USED_BY',
  'ASSOCIATED_WITH',
];

export default function GraphFilters({
  searchQuery,
  onSearchChange,
  selectedEntityType,
  onEntityTypeChange,
  selectedRelType,
  onRelTypeChange,
}: Props) {
  return (
    <div className="bg-white border-b border-[#E7E2D8] p-4 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 text-xs">
      {/* Search Bar */}
      <div className="flex-1 max-w-md relative">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search people, institutions, discoveries..."
          className="w-full pl-9 pr-4 py-2 bg-[#FAF8F5] border border-[#E7E2D8] text-[#1C1917] focus:outline-none focus:border-[#1C1917] rounded-sm"
        />
        <span className="absolute left-3 top-2.5 text-[#737373] text-xs">🔍</span>
      </div>

      {/* Type Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <label htmlFor="entity-type-filter" className="text-[10px] font-bold text-[#737373] uppercase tracking-wider">
            Entity Type:
          </label>
          <select
            id="entity-type-filter"
            aria-label="Entity Type"
            value={selectedEntityType}
            onChange={(e) => onEntityTypeChange(e.target.value)}
            className="py-1.5 px-2.5 bg-[#FAF8F5] border border-[#E7E2D8] text-[#1C1917] font-medium rounded-sm focus:outline-none focus:border-[#1C1917]"
          >
            {ENTITY_TYPES.map((t) => (
              <option key={t} value={t}>
                {t === 'ALL' ? 'All Entities' : t}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label htmlFor="relationship-filter" className="text-[10px] font-bold text-[#737373] uppercase tracking-wider">
            Relationship:
          </label>
          <select
            id="relationship-filter"
            aria-label="Relationship"
            value={selectedRelType}
            onChange={(e) => onRelTypeChange(e.target.value)}
            className="py-1.5 px-2.5 bg-[#FAF8F5] border border-[#E7E2D8] text-[#1C1917] font-medium rounded-sm focus:outline-none focus:border-[#1C1917]"
          >
            {REL_TYPES.map((r) => (
              <option key={r} value={r}>
                {r === 'ALL' ? 'All Relationships' : r}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
