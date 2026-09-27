'use client';

import React, { useState } from 'react';
import { Failure } from '@/types';
import { 
  AlertOctagon, 
  Wrench, 
  Code2, 
  CheckCheck, 
  Copy, 
  ShieldAlert, 
  FileTerminal,
  Layers
} from 'lucide-react';

interface FailureDiagnosticsProps {
  failures: Failure[];
}

export const FailureDiagnostics: React.FC<FailureDiagnosticsProps> = ({ failures }) => {
  const [copiedPatch, setCopiedPatch] = useState(false);

  if (!failures || failures.length === 0) {
    return null;
  }

  const handleCopyFix = (remediation: string) => {
    navigator.clipboard.writeText(remediation);
    setCopiedPatch(true);
    setTimeout(() => setCopiedPatch(false), 2000);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center space-x-2 text-rose-400">
        <AlertOctagon className="h-5 w-5" />
        <h3 className="text-sm font-bold uppercase tracking-wider">
          Failure Diagnosis & Engineering Feedback Package
        </h3>
      </div>

      {failures.map(failure => (
        <div
          key={failure.failure_id}
          className="rounded-xl border border-rose-500/30 bg-[#160b13] p-5 shadow-2xl space-y-4"
        >
          {/* Failure Header */}
          <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-rose-900/40">
            <div className="flex items-center space-x-2">
              <span className="px-2.5 py-1 rounded-md text-xs font-mono font-bold uppercase bg-rose-500/20 text-rose-300 border border-rose-500/40">
                {failure.category}
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-amber-500/10 text-amber-300 border border-amber-500/30">
                SEVERITY: {failure.severity}
              </span>
            </div>
            <span className="text-xs font-mono text-slate-400">
              ID: {failure.failure_id}
            </span>
          </div>

          {/* Title & Message */}
          <div>
            <h4 className="text-base font-bold text-white">
              {failure.title}
            </h4>
            <p className="mt-1 text-xs text-rose-200/90 font-sans">
              {failure.message}
            </p>
          </div>

          {/* Stack Trace */}
          {failure.stack_trace && (
            <div className="space-y-1.5">
              <div className="flex items-center space-x-1.5 text-xs font-mono text-slate-400">
                <FileTerminal className="h-3.5 w-3.5 text-rose-400" />
                <span>Diagnostic Stack Trace:</span>
              </div>
              <pre className="p-3.5 rounded-lg bg-slate-950 text-[11px] font-mono text-rose-300/90 border border-rose-950 overflow-x-auto whitespace-pre leading-relaxed">
                {failure.stack_trace}
              </pre>
            </div>
          )}

          {/* Remediation Package */}
          {failure.suggested_remediation && (
            <div className="p-4 rounded-xl bg-slate-950/80 border border-indigo-500/30 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-xs font-bold text-indigo-300 uppercase tracking-wider font-mono">
                  <Wrench className="h-4 w-4 text-cyan-400" />
                  <span>Coding-Agent Remediation Spec</span>
                </div>
                <button
                  onClick={() => handleCopyFix(failure.suggested_remediation || '')}
                  className="flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 text-xs transition-colors"
                >
                  {copiedPatch ? (
                    <>
                      <CheckCheck className="h-3.5 w-3.5 text-emerald-400" />
                      <span className="text-emerald-400 text-[11px]">Copied Spec</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5 text-slate-400" />
                      <span className="text-[11px]">Copy Fix Spec</span>
                    </>
                  )}
                </button>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed font-sans">
                {failure.suggested_remediation}
              </p>

              <div className="p-2.5 rounded bg-indigo-950/30 border border-indigo-500/20 text-[11px] text-indigo-200/80 flex items-center space-x-2">
                <ShieldAlert className="h-3.5 w-3.5 text-indigo-400 flex-shrink-0" />
                <span>
                  Engineering Feedback Loop: This structured diagnostic payload is ready for dispatch to an automated Coding Agent (e.g. Qwen2.5-Coder) for isolated branch patching and regression re-testing.
                </span>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
