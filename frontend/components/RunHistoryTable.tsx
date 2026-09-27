'use client';

import React from 'react';
import Link from 'next/link';
import { TestRun } from '@/types';
import { StatusBadge } from './StatusBadge';
import { formatDuration, formatDate } from '@/lib/utils';
import { ArrowRight, Database, AlertCircle, Layers } from 'lucide-react';

interface RunHistoryTableProps {
  runs: TestRun[];
  isLoading?: boolean;
}

export const RunHistoryTable: React.FC<RunHistoryTableProps> = ({
  runs,
  isLoading,
}) => {
  if (isLoading) {
    return (
      <div className="p-12 text-center text-slate-500 rounded-xl border border-slate-800 bg-[#0c1220]">
        Loading test runs telemetry...
      </div>
    );
  }

  if (!runs || runs.length === 0) {
    return (
      <div className="p-12 text-center text-slate-500 rounded-xl border border-slate-800 bg-[#0c1220]">
        No test runs recorded yet. Click &quot;Launch Test Run&quot; above to initiate your first execution slice.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-surface-border bg-[#0b1120] shadow-xl">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-950/80 text-slate-400 font-mono uppercase tracking-wider border-b border-slate-800 text-[11px]">
            <tr>
              <th className="py-3.5 px-4 font-semibold">Run ID</th>
              <th className="py-3.5 px-4 font-semibold">Target Application</th>
              <th className="py-3.5 px-4 font-semibold">Test Mode</th>
              <th className="py-3.5 px-4 font-semibold">Status</th>
              <th className="py-3.5 px-4 font-semibold">Duration</th>
              <th className="py-3.5 px-4 font-semibold">Evidence</th>
              <th className="py-3.5 px-4 font-semibold">Executed At</th>
              <th className="py-3.5 px-4 font-semibold text-right">Inspection</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-sans">
            {runs.map(run => {
              const evidenceCount = run.evidence_ids?.length || 0;
              const failureCount = run.failure_ids?.length || 0;

              return (
                <tr
                  key={run.run_id}
                  className="hover:bg-slate-900/40 transition-colors group"
                >
                  {/* Run ID */}
                  <td className="py-3 px-4 font-mono font-bold text-slate-200">
                    <Link
                      href={`/runs/${run.run_id}`}
                      className="text-indigo-400 hover:text-indigo-300 hover:underline"
                    >
                      {run.run_id}
                    </Link>
                  </td>

                  {/* Target Application */}
                  <td className="py-3 px-4">
                    <div className="font-semibold text-white">
                      {run.application_id}
                    </div>
                    <div className="text-[11px] text-slate-500 font-mono">
                      v{run.application_version}
                    </div>
                  </td>

                  {/* Test Mode */}
                  <td className="py-3 px-4">
                    <span className="px-2 py-0.5 rounded-md text-[10px] font-mono uppercase bg-slate-900 text-slate-300 border border-slate-800 font-medium">
                      {run.test_mode}
                    </span>
                  </td>

                  {/* Status */}
                  <td className="py-3 px-4">
                    <StatusBadge status={run.status} size="sm" />
                  </td>

                  {/* Duration */}
                  <td className="py-3 px-4 font-mono text-slate-300">
                    {formatDuration(run.duration_ms)}
                  </td>

                  {/* Evidence Count */}
                  <td className="py-3 px-4">
                    <div className="flex items-center space-x-2">
                      <span className="flex items-center space-x-1 text-slate-300 font-mono text-[11px]">
                        <Database className="h-3 w-3 text-cyan-400" />
                        <span>{evidenceCount}</span>
                      </span>
                      {failureCount > 0 && (
                        <span className="flex items-center space-x-0.5 px-1.5 py-0.5 rounded text-[10px] font-mono bg-rose-500/10 text-rose-400 border border-rose-500/20 font-bold">
                          <AlertCircle className="h-3 w-3" />
                          <span>{failureCount} fail</span>
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Executed At */}
                  <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                    {formatDate(run.started_at)}
                  </td>

                  {/* Action Link */}
                  <td className="py-3 px-4 text-right">
                    <Link
                      href={`/runs/${run.run_id}`}
                      className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-indigo-600/20 text-slate-400 hover:text-indigo-300 border border-slate-800 hover:border-indigo-500/30 font-medium transition-all"
                    >
                      <span>Inspect</span>
                      <ArrowRight className="h-3 w-3" />
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
