import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 text-center">
      <div className="max-w-3xl space-y-6">
        <div className="inline-block rounded-full bg-sky-500/10 px-4 py-1.5 text-sm font-medium text-sky-400 border border-sky-500/20">
          Phase 0 — Repository Foundation
        </div>
        <h1 className="text-5xl font-extrabold tracking-tight text-white sm:text-6xl">
          Project Matilda
        </h1>
        <p className="text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed">
          AI-powered historical representation auditor for educational material. Grounding historical analysis in structured evidence and verifiable knowledge graphs.
        </p>
        <div className="pt-4 flex justify-center gap-4">
          <Link
            href="/health"
            className="rounded-lg bg-sky-600 px-6 py-3 font-semibold text-white transition hover:bg-sky-500 shadow-lg shadow-sky-600/20"
          >
            System Status Check
          </Link>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg bg-slate-800 px-6 py-3 font-semibold text-slate-300 transition hover:bg-slate-700 border border-slate-700"
          >
            API OpenAPI Docs ↗
          </a>
        </div>
      </div>
    </main>
  );
}
