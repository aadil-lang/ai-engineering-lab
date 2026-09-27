'use client';

import React, { useState } from 'react';
import { 
  TestAction, 
  Evidence 
} from '@/types';
import { 
  Navigation, 
  Crosshair, 
  MousePointerClick, 
  Keyboard, 
  Send, 
  CheckCircle2, 
  XCircle, 
  ChevronDown, 
  ChevronRight, 
  FileText,
  Clock,
  Sparkles,
  MoveDown,
  Flag
} from 'lucide-react';
import { formatDuration } from '@/lib/utils';

interface ActionTimelineProps {
  actions: TestAction[];
  evidenceItems: Evidence[];
  onSelectEvidence?: (evidenceId: string) => void;
}

export const ActionTimeline: React.FC<ActionTimelineProps> = ({
  actions,
  evidenceItems,
  onSelectEvidence,
}) => {
  const [expandedActionId, setExpandedActionId] = useState<string | null>(
    actions.length > 0 ? actions[0].action_id : null
  );

  const getActionIcon = (type: string) => {
    switch (type) {
      case 'NAVIGATE':
        return <Navigation className="h-4 w-4 text-cyan-400" />;
      case 'LOCATE':
        return <Crosshair className="h-4 w-4 text-indigo-400" />;
      case 'INPUT':
        return <Keyboard className="h-4 w-4 text-amber-400" />;
      case 'CLICK':
        return <MousePointerClick className="h-4 w-4 text-emerald-400" />;
      case 'HOVER':
        return <MousePointerClick className="h-4 w-4 text-pink-400" />;
      case 'PRESS_KEY':
        return <Keyboard className="h-4 w-4 text-amber-300" />;
      case 'SCROLL':
        return <MoveDown className="h-4 w-4 text-blue-400" />;
      case 'FINISH':
        return <Flag className="h-4 w-4 text-purple-400" />;
      case 'SUBMIT':
      case 'ASSERT':
        return <Send className="h-4 w-4 text-purple-400" />;
      default:
        return <FileText className="h-4 w-4 text-slate-400" />;
    }
  };

  if (!actions || actions.length === 0) {
    return (
      <div className="p-8 text-center text-slate-500 rounded-xl border border-slate-800 bg-[#0c1220]">
        No actions recorded for this execution run.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {actions.map((action, index) => {
        const isExpanded = expandedActionId === action.action_id;
        const isPassed = action.status === 'PASSED';
        const isFailed = action.status === 'FAILED';

        // Find linked evidence for this action
        const linkedEvidence = evidenceItems.filter(
          e => e.action_id === action.action_id || action.evidence_ids?.includes(e.evidence_id)
        );

        return (
          <div
            key={action.action_id}
            className={`rounded-xl border transition-all duration-200 overflow-hidden ${
              isFailed
                ? 'border-rose-500/40 bg-[#160d14]/70 shadow-[0_0_15px_rgba(244,63,94,0.1)]'
                : isExpanded
                ? 'border-indigo-500/40 bg-[#0d1529]/90 shadow-lg'
                : 'border-surface-border bg-[#0b1120]/70 hover:border-slate-700'
            }`}
          >
            {/* Header / Summary Bar */}
            <button
              onClick={() => setExpandedActionId(isExpanded ? null : action.action_id)}
              className="w-full px-4 py-3.5 flex items-center justify-between text-left focus:outline-none"
            >
              <div className="flex items-center space-x-3 min-w-0">
                {/* Step Number & Icon */}
                <div className="flex items-center space-x-2 flex-shrink-0">
                  <span className="flex items-center justify-center h-6 w-6 rounded-full bg-slate-900 border border-slate-800 text-[11px] font-mono text-slate-400 font-bold">
                    {index + 1}
                  </span>
                  <div className="p-1.5 rounded-lg bg-slate-900/90 border border-slate-800">
                    {getActionIcon(action.action_type)}
                  </div>
                </div>

                {/* Description & Type */}
                <div className="min-w-0">
                  <div className="flex items-center space-x-2 flex-wrap">
                    <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300">
                      {action.action_type}
                    </span>
                    {action.selector && (
                      <span className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700/80 text-[10px] font-mono text-cyan-300">
                        {action.selector}
                      </span>
                    )}
                    <span className="text-[11px] text-slate-500 font-mono">
                      {action.action_id}
                    </span>
                  </div>
                  
                  {/* Agent Thought Callout */}
                  {action.thought && (
                    <div className="mt-1 flex items-start space-x-1.5 text-xs text-purple-300/90 italic bg-purple-950/30 px-2 py-1 rounded-md border border-purple-500/20">
                      <Sparkles className="h-3 w-3 text-purple-400 mt-0.5 flex-shrink-0" />
                      <span className="line-clamp-2">{action.thought}</span>
                    </div>
                  )}

                  {!action.thought && (
                    <p className="text-xs text-slate-300 truncate mt-0.5 font-sans">
                      {action.description}
                    </p>
                  )}
                </div>
              </div>

              {/* Status, Latency & Toggle */}
              <div className="flex items-center space-x-3 flex-shrink-0 pl-3">
                <div className="flex items-center space-x-1.5 text-xs text-slate-400 font-mono">
                  <Clock className="h-3 w-3 text-slate-500" />
                  <span>{formatDuration(action.duration_ms)}</span>
                </div>

                {isPassed && (
                  <span className="flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    <CheckCircle2 className="h-3 w-3" />
                    <span>PASS</span>
                  </span>
                )}
                {isFailed && (
                  <span className="flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30">
                    <XCircle className="h-3 w-3" />
                    <span>FAIL</span>
                  </span>
                )}

                <div className="text-slate-500">
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                </div>
              </div>
            </button>

            {/* Expanded Payload & Evidence */}
            {isExpanded && (
              <div className="px-4 pb-4 pt-1 border-t border-slate-800/80 bg-slate-950/40 text-xs space-y-3">
                {/* Error Banner if Failed */}
                {action.error_message && (
                  <div className="p-3 rounded-lg bg-rose-950/30 border border-rose-500/30 text-rose-300 font-mono text-[11px]">
                    <div className="font-bold text-rose-400 mb-1 flex items-center space-x-1.5">
                      <XCircle className="h-3.5 w-3.5" />
                      <span>Execution Error:</span>
                    </div>
                    {action.error_message}
                  </div>
                )}

                {/* Input / Output Grids */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {/* Inputs */}
                  <div className="rounded-lg border border-slate-800/80 bg-slate-900/60 p-3">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold block mb-2">
                      Input Arguments:
                    </span>
                    <pre className="text-[11px] font-mono text-cyan-300/90 whitespace-pre-wrap overflow-x-auto max-h-40">
                      {JSON.stringify(action.input_data, null, 2)}
                    </pre>
                  </div>

                  {/* Outputs */}
                  <div className="rounded-lg border border-slate-800/80 bg-slate-900/60 p-3">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold block mb-2">
                      Output / Telemetry Response:
                    </span>
                    <pre className="text-[11px] font-mono text-emerald-300/90 whitespace-pre-wrap overflow-x-auto max-h-40">
                      {JSON.stringify(action.output_data, null, 2)}
                    </pre>
                  </div>
                </div>

                {/* Linked Evidence Buttons */}
                {linkedEvidence.length > 0 && (
                  <div className="pt-2 flex items-center space-x-2 flex-wrap">
                    <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                      Structured Evidence:
                    </span>
                    {linkedEvidence.map(evi => (
                      <button
                        key={evi.evidence_id}
                        onClick={() => onSelectEvidence && onSelectEvidence(evi.evidence_id)}
                        className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-[11px] font-mono transition-colors"
                      >
                        <FileText className="h-3 w-3 text-indigo-400" />
                        <span>{evi.title}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
