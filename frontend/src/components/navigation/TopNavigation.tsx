'use client';

import { Suspense } from 'react';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';

function NavLinks() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const docId = searchParams.get('id');

  const querySuffix = docId ? `?id=${docId}` : '';

  const navLinks = [
    { name: 'UPLOAD', href: '/upload' },
    { name: 'WORKSPACE', href: `/workspace${querySuffix}` },
    { name: 'KNOWLEDGE GRAPH', href: `/graph${querySuffix}` },
    { name: 'REPORTS', href: `/reports${querySuffix}` },
  ];

  return (
    <nav className="flex items-center gap-8">
      {navLinks.map((link) => {
        const baseHref = link.href.split('?')[0];
        const isActive =
          pathname === baseHref ||
          (baseHref !== '/' && pathname.startsWith(baseHref));
        return (
          <Link
            key={link.name}
            href={link.href}
            className={`text-xs font-semibold tracking-wider transition-all py-1.5 border-b-2 ${
              isActive
                ? 'text-[#1C1917] border-[#1C1917]'
                : 'text-[#737373] border-transparent hover:text-[#1C1917] hover:border-[#D6CFBF]'
            }`}
          >
            {link.name}
          </Link>
        );
      })}
    </nav>
  );
}

export default function TopNavigation() {
  return (
    <header className="sticky top-0 z-40 bg-[#FAF8F5]/95 backdrop-blur-sm border-b border-[#E7E2D8] px-6 py-3 transition-colors">
      <div className="max-w-[1600px] mx-auto flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-10">
          <Link href="/workspace" className="group">
            <span className="font-serif text-2xl font-bold tracking-tight text-[#1C1917] group-hover:text-[#4A463D] transition-colors">
              MATILDA
            </span>
          </Link>

          {/* Navigation Links with Suspense */}
          <Suspense fallback={
            <nav className="flex items-center gap-8">
              <span className="text-xs font-semibold text-[#737373]">UPLOAD</span>
              <span className="text-xs font-semibold text-[#737373]">WORKSPACE</span>
              <span className="text-xs font-semibold text-[#737373]">KNOWLEDGE GRAPH</span>
              <span className="text-xs font-semibold text-[#737373]">REPORTS</span>
            </nav>
          }>
            <NavLinks />
          </Suspense>
        </div>

        {/* Right side user profile icon */}
        <div className="flex items-center gap-4">
          <div className="text-right hidden sm:block">
            <p className="text-xs font-semibold text-[#1C1917]">Scholarly Auditor</p>
            <p className="text-[10px] text-[#737373] uppercase tracking-wider">Research Access</p>
          </div>
          <button
            aria-label="User Profile"
            className="w-8 h-8 rounded-full bg-[#E7E2D8] border border-[#D6CFBF] flex items-center justify-center text-[#1C1917] hover:bg-[#D6CFBF] transition-colors text-xs font-bold font-mono"
          >
            SA
          </button>
        </div>
      </div>
    </header>
  );
}
