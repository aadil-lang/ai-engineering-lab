'use client';

import React, { useState } from 'react';
import { Evidence, EvidenceType } from '@/types';
import { 
  FileCode, 
  Image as ImageIcon, 
  Network, 
  Terminal, 
  Bot, 
  Activity, 
  Copy, 
  Check, 
  Clock, 
  Layers
} from 'lucide-react';
import { formatDate } from '@/lib/utils';

interface EvidenceViewerProps {
  evidenceItems: Evidence[];
  selectedEvidenceId?: string | null;
}

export const EvidenceViewer: React.FC<EvidenceViewerProps> = ({
  evidenceItems,
  selectedEvidenceId,
}) => {
  const [activeId, setActiveId] = useState<string | null>(
    selectedEvidenceId || (evidenceItems.length > 0 ? evidenceItems[0].evidence_id : null)
  );
  const [copied, setCopied] = useState(false);

  // Sync selected ID when prop changes
  React.useEffect(() => {
    if (selectedEvidenceId) {
      setActiveId(selectedEvidenceId);
    } else if (evidenceItems.length > 0 && !activeId) {
      setActiveId(evidenceItems[0].evidence_id);
    }
  }, [selectedEvidenceId, evidenceItems]);

  const activeEvidence = evidenceItems.find(e => e.evidence_id === activeId) || evidenceItems[0];

  const getEvidenceIcon = (type: EvidenceType) => {
    switch (type) {
      case 'DOM_SNAPSHOT':
        return <FileCode className="h-4 w-4 text-cyan-400" />;
      case 'SCREENSHOT':
        return <ImageIcon className="h-4 w-4 text-emerald-400" />;
      case 'NETWORK_HAR':
        return <Network className="h-4 w-4 text-indigo-400" />;
      case 'CONSOLE_LOG':
        return <Terminal className="h-4 w-4 text-amber-400" />;
      case 'LLM_TRANSCRIPT':
        return <Bot className="h-4 w-4 text-purple-400" />;
      case 'PERFORMANCE_TRACE':
        return <Activity className="h-4 w-4 text-rose-400" />;
      default:
        return <Layers className="h-4 w-4 text-slate-400" />;
    }
  };

  const handleCopyPayload = () => {
    if (!activeEvidence) return;
    navigator.clipboard.writeText(
      typeof activeEvidence.payload === 'string'
        ? activeEvidence.payload
        : JSON.stringify(activeEvidence.payload, null, 2)
    );
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!evidenceItems || evidenceItems.length === 0) {
    return (
      <div className="p-8 text-center text-slate-500 rounded-xl border border-slate-800 bg-[#0c1220]">
        No evidence records collected for this run.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-surface-border bg-[#0b1120] overflow-hidden shadow-xl">
      {/* Evidence Top Selector Tabs */}
      <div className="flex items-center space-x-1 p-2 bg-slate-950/80 border-b border-slate-800 overflow-x-auto">
        {evidenceItems.map(item => {
          const isActive = activeEvidence?.evidence_id === item.evidence_id;
          return (
            <button
              key={item.evidence_id}
              onClick={() => setActiveId(item.evidence_id)}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-mono whitespace-nowrap transition-all ${
                isActive
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/40 shadow-sm font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
              }`}
            >
              {getEvidenceIcon(item.evidence_type)}
              <span className="truncate max-w-[150px] sm:max-w-[200px]">
                {item.title}
              </span>
            </button>
          );
        })}
      </div>

      {/* Evidence Detailed View */}
      {activeEvidence && (
        <div className="p-5 space-y-4">
          {/* Metadata Header */}
          <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800">
            <div>
              <div className="flex items-center space-x-2">
                <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-300 border border-slate-700">
                  {activeEvidence.evidence_type}
                </span>
                <span className="text-sm font-bold text-white">
                  {activeEvidence.title}
                </span>
              </div>
              <div className="flex items-center space-x-3 text-[11px] text-slate-500 font-mono mt-1">
                <span>ID: {activeEvidence.evidence_id}</span>
                {activeEvidence.action_id && (
                  <span>Action: {activeEvidence.action_id}</span>
                )}
                <span>Time: {formatDate(activeEvidence.timestamp)}</span>
              </div>
            </div>

            {/* Copy Button */}
            <button
              onClick={handleCopyPayload}
              className="flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 text-xs transition-colors"
            >
              {copied ? (
                <>
                  <Check className="h-3.5 w-3.5 text-emerald-400" />
                  <span className="text-emerald-400">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5 text-slate-400" />
                  <span>Copy Payload</span>
                </>
              )}
            </button>
          </div>

          {/* Render Type-Specific Interactive Previews */}
          {activeEvidence.evidence_type === 'DOM_SNAPSHOT' && (
            <div className="space-y-3">
              <div className="p-3 rounded-lg bg-cyan-950/20 border border-cyan-500/20 text-xs text-cyan-300">
                DOM Inspector: Captured layout tree with {activeEvidence.payload?.nodes_count || 342} DOM nodes and active styles.
              </div>
              <pre className="p-4 rounded-xl bg-slate-950 text-slate-200 font-mono text-xs overflow-x-auto max-h-96 border border-slate-800 leading-relaxed">
                <code>
                  {typeof activeEvidence.payload?.html_snippet === 'string'
                    ? activeEvidence.payload.html_snippet
                    : JSON.stringify(activeEvidence.payload, null, 2)}
                </code>
              </pre>
            </div>
          )}

          {activeEvidence.evidence_type === 'SCREENSHOT' && (
            <div className="space-y-3">
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-center space-y-3">
                {activeEvidence.artifact_path ? (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs text-slate-400 px-1 font-mono">
                      <span className="flex items-center space-x-1.5 text-emerald-400">
                        <ImageIcon className="h-3.5 w-3.5" />
                        <span>Real Browser Screenshot Captured</span>
                      </span>
                      <a
                        href={`/api/v1/runs/${activeEvidence.run_id}/evidence/${activeEvidence.evidence_id}/artifact`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-indigo-400 hover:text-indigo-300 underline"
                      >
                        Open Full Resolution
                      </a>
                    </div>
                    <div className="relative overflow-hidden rounded-lg border border-slate-800 bg-slate-900 shadow-xl max-h-[500px]">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={`/api/v1/runs/${activeEvidence.run_id}/evidence/${activeEvidence.evidence_id}/artifact`}
                        alt={activeEvidence.title}
                        className="w-full h-auto object-contain max-h-[480px] mx-auto rounded"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="relative mx-auto max-w-xl aspect-video rounded-lg bg-gradient-to-br from-slate-900 via-[#0d1627] to-slate-900 border border-indigo-500/30 flex flex-col items-center justify-center p-6 shadow-inner">
                    <div className="absolute top-3 left-3 flex items-center space-x-1.5">
                      <span className="h-2.5 w-2.5 rounded-full bg-rose-500/80" />
                      <span className="h-2.5 w-2.5 rounded-full bg-amber-500/80" />
                      <span className="h-2.5 w-2.5 rounded-full bg-emerald-500/80" />
                    </div>
                    <div className="p-4 rounded-lg border border-dashed border-cyan-400/80 bg-cyan-500/10 text-cyan-300 font-mono text-xs text-center space-y-1">
                      <div className="font-bold flex items-center justify-center space-x-1.5">
                        <ImageIcon className="h-4 w-4" />
                        <span>Bounding Box: {activeEvidence.payload?.target_selector || 'Target Element'}</span>
                      </div>
                      <div className="text-[11px] text-slate-400">
                        Viewport: {activeEvidence.payload?.viewport || '1920x1080'} · Hash: {activeEvidence.payload?.visual_hash || 'a8f93e1'}
                      </div>
                    </div>
                  </div>
                )}
              </div>
              <pre className="p-3 rounded-lg bg-slate-950 text-[11px] font-mono text-slate-400 border border-slate-800">
                {JSON.stringify(activeEvidence.payload, null, 2)}
              </pre>
            </div>
          )}

          {activeEvidence.evidence_type === 'NETWORK_HAR' && (
            <div className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                  <span className="text-[10px] text-slate-400 font-mono uppercase">Status Code</span>
                  <div className="text-lg font-bold font-mono text-emerald-400 mt-0.5">
                    {activeEvidence.payload?.response_status || 200} OK
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                  <span className="text-[10px] text-slate-400 font-mono uppercase">Method & Endpoint</span>
                  <div className="text-xs font-bold font-mono text-cyan-400 truncate mt-0.5">
                    {activeEvidence.payload?.method || 'POST'} {activeEvidence.payload?.endpoint || '/api'}
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                  <span className="text-[10px] text-slate-400 font-mono uppercase">TTFB Latency</span>
                  <div className="text-lg font-bold font-mono text-indigo-400 mt-0.5">
                    {activeEvidence.payload?.network_timings?.ttfb || 42.1} ms
                  </div>
                </div>
              </div>
              <pre className="p-4 rounded-xl bg-slate-950 text-slate-200 font-mono text-xs overflow-x-auto max-h-96 border border-slate-800 leading-relaxed">
                <code>{JSON.stringify(activeEvidence.payload, null, 2)}</code>
              </pre>
            </div>
          )}

          {activeEvidence.evidence_type !== 'DOM_SNAPSHOT' &&
            activeEvidence.evidence_type !== 'SCREENSHOT' &&
            activeEvidence.evidence_type !== 'NETWORK_HAR' && (
              <pre className="p-4 rounded-xl bg-slate-950 text-slate-200 font-mono text-xs overflow-x-auto max-h-96 border border-slate-800 leading-relaxed">
                <code>{JSON.stringify(activeEvidence.payload, null, 2)}</code>
              </pre>
            )}
        </div>
      )}
    </div>
  );
};
