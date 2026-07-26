'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api-client';
import { HealthResponse } from '@/types/api';

export default function HealthPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getHealth();
      setHealth(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to connect to backend service.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <main className="min-h-screen bg-slate-900 p-8 flex flex-col items-center justify-center">
      <div className="w-full max-w-md bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-xl space-y-6">
        <div className="flex items-center justify-between border-b border-slate-700 pb-4">
          <h2 className="text-xl font-bold text-white">System Diagnostics</h2>
          <Link href="/" className="text-sm text-sky-400 hover:underline">
            ← Home
          </Link>
        </div>

        {loading ? (
          <div className="text-center py-8 text-slate-400">Pinging backend health endpoint...</div>
        ) : error ? (
          <div className="space-y-4">
            <div className="p-4 rounded-lg bg-red-950/50 border border-red-800 text-red-300 text-sm">
              <span className="font-semibold block mb-1">Connection Error</span>
              {error}
            </div>
            <button
              onClick={fetchHealth}
              className="w-full py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition font-medium"
            >
              Retry Connection
            </button>
          </div>
        ) : health ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 rounded-lg bg-emerald-950/40 border border-emerald-800/60">
              <span className="text-sm font-medium text-slate-300">Status</span>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                ● {health.status}
              </span>
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex justify-between py-1.5 border-b border-slate-700/50 text-slate-400">
                <span>Application</span>
                <span className="text-slate-200 font-medium">{health.app_name}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-700/50 text-slate-400">
                <span>Environment</span>
                <span className="text-slate-200 font-medium">{health.environment}</span>
              </div>
              <div className="flex justify-between py-1.5 text-slate-400">
                <span>Version</span>
                <span className="text-slate-200 font-medium">{health.version}</span>
              </div>
            </div>

            <button
              onClick={fetchHealth}
              className="w-full py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg transition font-medium text-sm shadow-md"
            >
              Refresh Health Status
            </button>
          </div>
        ) : null}
      </div>
    </main>
  );
}
