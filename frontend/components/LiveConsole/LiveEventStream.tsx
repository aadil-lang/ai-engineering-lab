'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  LiveEventModel,
  LiveEventType,
} from '@/types';
import {
  Activity,
  Terminal,
  Globe,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Camera,
  Layers,
  Cpu,
  ChevronDown,
  ChevronRight,
  Filter,
  ArrowDown,
  Search,
  Sparkles,
  ShieldCheck,
  Wrench,
  Bug,
} from 'lucide-react';

interface LiveEventStreamProps {
  events: LiveEventModel[];
  isConnected?: boolean;
}

const EVENT_TYPE_CONFIG: Record<
  string,
  { label: string; icon: React.ReactNode; color: string; badgeBg: string }
> = {
  SESSION_CREATED: {
    label: 'Session Created',
    icon: <Sparkles className="h-3.5 w-3.5 text-indigo-400" />,
    color: 'text-indigo-400',
    badgeBg: 'bg-indigo-950/60 border-indigo-500/30',
  },
  SESSION_STARTED: {
    label: 'Session Started',
    icon: <Activity className="h-3.5 w-3.5 text-cyan-400" />,
    color: 'text-cyan-400',
    badgeBg: 'bg-cyan-950/60 border-cyan-500/30',
  },
  NAVIGATION_STARTED: {
    label: 'Navigation Started',
    icon: <Globe className="h-3.5 w-3.5 text-sky-400" />,
    color: 'text-sky-400',
    badgeBg: 'bg-sky-950/60 border-sky-500/30',
  },
  NAVIGATION_COMPLETED: {
    label: 'Navigation Ready',
    icon: <Globe className="h-3.5 w-3.5 text-emerald-400" />,
    color: 'text-emerald-400',
    badgeBg: 'bg-emerald-950/60 border-emerald-500/30',
  },
  DOM_OBSERVED: {
    label: 'DOM Observed',
    icon: <Layers className="h-3.5 w-3.5 text-purple-400" />,
    color: 'text-purple-400',
    badgeBg: 'bg-purple-950/60 border-purple-500/30',
  },
  ACTION_STARTED: {
    label: 'Action Dispatched',
    icon: <Activity className="h-3.5 w-3.5 text-amber-400 animate-spin" />,
    color: 'text-amber-400',
    badgeBg: 'bg-amber-950/60 border-amber-500/30',
  },
  ACTION_COMPLETED: {
    label: 'Action Passed',
    icon: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />,
    color: 'text-emerald-400',
    badgeBg: 'bg-emerald-950/60 border-emerald-500/30',
  },
  ACTION_FAILED: {
    label: 'Action Failed',
    icon: <XCircle className="h-3.5 w-3.5 text-rose-400" />,
    color: 'text-rose-400',
    badgeBg: 'bg-rose-950/60 border-rose-500/30',
  },
  SCREENSHOT_CAPTURED: {
    label: 'Screenshot Captured',
    icon: <Camera className="h-3.5 w-3.5 text-cyan-400" />,
    color: 'text-cyan-400',
    badgeBg: 'bg-cyan-950/60 border-cyan-500/30',
  },
  CONSOLE_EVENT: {
    label: 'Console Output',
    icon: <Terminal className="h-3.5 w-3.5 text-amber-400" />,
    color: 'text-amber-300',
    badgeBg: 'bg-slate-900 border-slate-700',
  },
  PAGE_ERROR: {
    label: 'Page Error',
    icon: <AlertTriangle className="h-3.5 w-3.5 text-rose-400" />,
    color: 'text-rose-400',
    badgeBg: 'bg-rose-950/80 border-rose-500/40',
  },
  NETWORK_REQUEST_STARTED: {
    label: 'Network Req',
    icon: <Globe className="h-3.5 w-3.5 text-slate-400" />,
    color: 'text-slate-300',
    badgeBg: 'bg-slate-900 border-slate-800',
  },
  NETWORK_REQUEST_COMPLETED: {
    label: 'Network 200 OK',
    icon: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />,
    color: 'text-emerald-400',
    badgeBg: 'bg-emerald-950/40 border-emerald-500/20',
  },
  NETWORK_REQUEST_FAILED: {
    label: 'Network Failed',
    icon: <XCircle className="h-3.5 w-3.5 text-rose-400" />,
    color: 'text-rose-400',
    badgeBg: 'bg-rose-950/60 border-rose-500/40',
  },
  PERFORMANCE_UPDATE: {
    label: 'Performance',
    icon: <Cpu className="h-3.5 w-3.5 text-indigo-400" />,
    color: 'text-indigo-300',
    badgeBg: 'bg-indigo-950/40 border-indigo-500/30',
  },
  ASSERTION_PASSED: {
    label: 'Assertion OK',
    icon: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />,
    color: 'text-emerald-400',
    badgeBg: 'bg-emerald-950/60 border-emerald-500/30',
  },
  ASSERTION_FAILED: {
    label: 'Assertion Violation',
    icon: <XCircle className="h-3.5 w-3.5 text-rose-400" />,
    color: 'text-rose-400',
    badgeBg: 'bg-rose-950/80 border-rose-500/50',
  },
  DETERMINISTIC_EVALUATION_COMPLETED: {
    label: 'Deterministic Authority',
    icon: <ShieldCheck className="h-3.5 w-3.5 text-cyan-400" />,
    color: 'text-cyan-300',
    badgeBg: 'bg-cyan-950/60 border-cyan-500/40',
  },
  DIAGNOSIS_COMPLETED: {
    label: 'AI Causal Diagnosis',
    icon: <Bug className="h-3.5 w-3.5 text-rose-400" />,
    color: 'text-rose-300',
    badgeBg: 'bg-rose-950/70 border-rose-500/40',
  },
  REMEDIATION_PROPOSED: {
    label: 'Remediation Proposed',
    icon: <Wrench className="h-3.5 w-3.5 text-purple-400" />,
    color: 'text-purple-300',
    badgeBg: 'bg-purple-950/70 border-purple-500/40',
  },
  STRATEGY_PLANNED: {
    label: 'Strategy Planned',
    icon: <Sparkles className="h-3.5 w-3.5 text-blue-400" />,
    color: 'text-blue-300',
    badgeBg: 'bg-blue-950/70 border-blue-500/40',
  },
  STRATEGY_ADAPTED: {
    label: 'Strategy Adapted',
    icon: <Activity className="h-3.5 w-3.5 text-amber-400" />,
    color: 'text-amber-300',
    badgeBg: 'bg-amber-950/70 border-amber-500/40',
  },
  MEMORY_RETRIEVAL_STARTED: {
    label: 'Memory Search',
    icon: <Search className="h-3.5 w-3.5 text-cyan-400" />,
    color: 'text-cyan-300',
    badgeBg: 'bg-cyan-950/70 border-cyan-500/40',
  },
  MEMORY_RETRIEVAL_COMPLETED: {
    label: 'Memory Retrieved',
    icon: <Sparkles className="h-3.5 w-3.5 text-emerald-400" />,
    color: 'text-emerald-300',
    badgeBg: 'bg-emerald-950/70 border-emerald-500/40',
  },
  MEMORY_CANDIDATE_CREATED: {
    label: 'Candidate Proposed',
    icon: <Layers className="h-3.5 w-3.5 text-indigo-400" />,
    color: 'text-indigo-300',
    badgeBg: 'bg-indigo-950/70 border-indigo-500/40',
  },
  MEMORY_PROMOTED: {
    label: 'Memory Promoted',
    icon: <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />,
    color: 'text-emerald-300',
    badgeBg: 'bg-emerald-950/70 border-emerald-500/40',
  },
  MEMORY_INVALIDATED: {
    label: 'Memory Invalidated',
    icon: <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />,
    color: 'text-amber-300',
    badgeBg: 'bg-amber-950/70 border-amber-500/40',
  },
  MEMORY_CONTRADICTION_DETECTED: {
    label: 'Contradiction Preserved',
    icon: <AlertTriangle className="h-3.5 w-3.5 text-rose-400" />,
    color: 'text-rose-300',
    badgeBg: 'bg-rose-950/70 border-rose-500/40',
  },
  SESSION_COMPLETED: {
    label: 'Session Passed',
    icon: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />,
    color: 'text-emerald-300',
    badgeBg: 'bg-emerald-950/80 border-emerald-500/50',
  },
  SESSION_FAILED: {
    label: 'Session Failed',
    icon: <XCircle className="h-3.5 w-3.5 text-rose-400" />,
    color: 'text-rose-300',
    badgeBg: 'bg-rose-950/80 border-rose-500/50',
  },
  SESSION_CANCELLED: {
    label: 'Session Cancelled',
    icon: <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />,
    color: 'text-amber-300',
    badgeBg: 'bg-amber-950/80 border-amber-500/50',
  },
};

export const LiveEventStream: React.FC<LiveEventStreamProps> = ({
  events,
  isConnected = true,
}) => {
  const [filterType, setFilterType] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);
  const [autoScroll, setAutoScroll] = useState<boolean>(true);

  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new events
  useEffect(() => {
    if (autoScroll && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [events, autoScroll]);

  const filteredEvents = events.filter(e => {
    // Filter by category
    if (filterType === 'ACTIONS' && !e.event_type.startsWith('ACTION') && !e.event_type.startsWith('NAVIGATION')) {
      return false;
    }
    if (filterType === 'STRATEGY' && !e.event_type.startsWith('STRATEGY')) {
      return false;
    }
    if (filterType === 'MEMORY' && !e.event_type.startsWith('MEMORY')) {
      return false;
    }
    if (filterType === 'CONSOLE' && e.event_type !== 'CONSOLE_EVENT' && e.event_type !== 'PAGE_ERROR') {
      return false;
    }
    if (filterType === 'NETWORK' && !e.event_type.startsWith('NETWORK')) {
      return false;
    }
    if (filterType === 'ASSERTIONS' && !e.event_type.startsWith('ASSERTION') && !e.event_type.startsWith('DETERMINISTIC')) {
      return false;
    }

    // Filter by search query
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const payloadStr = JSON.stringify(e.payload).toLowerCase();
      const typeStr = e.event_type.toLowerCase();
      return typeStr.includes(q) || payloadStr.includes(q);
    }
    return true;
  });

  const toggleExpand = (eventId: string) => {
    setExpandedEventId(prev => (prev === eventId ? null : eventId));
  };

  return (
    <div className="flex flex-col h-[520px] lg:h-[620px] rounded-2xl border border-slate-800 bg-[#090d16] overflow-hidden shadow-2xl">
      {/* Header with connection indicator & stats */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-950 border-b border-slate-800/90 font-mono text-xs">
        <div className="flex items-center space-x-2">
          <Activity className="h-4 w-4 text-cyan-400" />
          <span className="font-bold text-white tracking-wide">Live Engineering Event Bus</span>
          <span className="px-2 py-0.5 rounded-full bg-slate-800 text-[10px] text-slate-300">
            {events.length} Events
          </span>
        </div>

        <div className="flex items-center space-x-2">
          {isConnected ? (
            <span className="inline-flex items-center space-x-1.5 text-[10px] text-emerald-400 font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span>SSE STREAMING</span>
            </span>
          ) : (
            <span className="inline-flex items-center space-x-1.5 text-[10px] text-slate-500">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-600" />
              <span>DISCONNECTED</span>
            </span>
          )}
        </div>
      </div>

      {/* Filter and Search Ribbon */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 bg-slate-900/60 border-b border-slate-800/80 text-[11px] font-mono">
        <div className="flex items-center space-x-1 overflow-x-auto">
          {['ALL', 'STRATEGY', 'MEMORY', 'ACTIONS', 'CONSOLE', 'NETWORK', 'ASSERTIONS'].map(f => (
            <button
              key={f}
              onClick={() => setFilterType(f)}
              className={`px-2.5 py-1 rounded-md transition ${
                filterType === f
                  ? 'bg-cyan-600/30 text-cyan-300 border border-cyan-500/40 font-bold'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800 border border-transparent'
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        <div className="flex items-center space-x-2">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-slate-500" />
            <input
              type="text"
              placeholder="Search events..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="pl-7 pr-2.5 py-1 rounded-md bg-slate-950 border border-slate-800 text-[11px] text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 w-32 sm:w-40"
            />
          </div>

          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`px-2 py-1 rounded-md text-[10px] transition ${
              autoScroll ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/40' : 'text-slate-500 hover:text-slate-300'
            }`}
            title="Toggle autoscroll to latest events"
          >
            Auto-Scroll: {autoScroll ? 'ON' : 'OFF'}
          </button>
        </div>
      </div>

      {/* Events List */}
      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto p-3 space-y-2 font-mono text-xs divide-y divide-slate-800/40"
      >
        {filteredEvents.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-6 space-y-2 text-slate-500">
            <Activity className="h-8 w-8 text-slate-700 animate-pulse" />
            <p className="text-xs">No events matching current filter</p>
          </div>
        ) : (
          filteredEvents.map(evt => {
            const cfg = EVENT_TYPE_CONFIG[evt.event_type] || {
              label: evt.event_type,
              icon: <Activity className="h-3.5 w-3.5 text-slate-400" />,
              color: 'text-slate-300',
              badgeBg: 'bg-slate-900 border-slate-800',
            };

            const isExpanded = expandedEventId === evt.event_id;

            return (
              <div
                key={evt.event_id}
                className="pt-2 first:pt-0 rounded-lg hover:bg-slate-900/40 px-2 py-1.5 transition"
              >
                <div
                  className="flex items-center justify-between cursor-pointer select-none"
                  onClick={() => toggleExpand(evt.event_id)}
                >
                  <div className="flex items-center space-x-2 truncate">
                    <span className="px-1.5 py-0.5 rounded bg-slate-950 border border-slate-800 text-[10px] text-slate-500 font-bold">
                      #{evt.sequence_number}
                    </span>

                    <span
                      className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-md border text-[10px] font-semibold ${cfg.badgeBg} ${cfg.color}`}
                    >
                      {cfg.icon}
                      <span>{cfg.label}</span>
                    </span>

                    {/* Summary text */}
                    <span className="truncate text-slate-300 text-[11px]">
                      {evt.payload?.content ||
                        (evt.payload?.total_retrieved !== undefined
                          ? `${evt.payload.total_retrieved} retrieved (${evt.payload.applicable_count} applicable, ${evt.payload.conflicting_count || 0} conflicts)`
                          : '') ||
                        evt.payload?.reason ||
                        evt.payload?.description ||
                        (evt.payload?.application_archetype ? `${evt.payload.application_archetype} [${evt.payload.strategy_mode}]` : '') ||
                        evt.payload?.url ||
                        evt.payload?.action_type ||
                        evt.payload?.assertion ||
                        evt.payload?.error ||
                        evt.payload?.text ||
                        ''}
                    </span>
                  </div>

                  <div className="flex items-center space-x-2 text-[10px] text-slate-500 flex-shrink-0">
                    <span>
                      {evt.timestamp ? new Date(evt.timestamp).toLocaleTimeString() : ''}
                    </span>
                    {isExpanded ? (
                      <ChevronDown className="h-3 w-3 text-slate-400" />
                    ) : (
                      <ChevronRight className="h-3 w-3 text-slate-600" />
                    )}
                  </div>
                </div>

                {/* Expanded Payload Inspector */}
                {isExpanded && (
                  <div className="mt-2 p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-[11px] text-slate-300 overflow-x-auto">
                    <div className="flex items-center justify-between pb-1.5 mb-1.5 border-b border-slate-800/80 text-[10px] text-slate-500">
                      <span>Event ID: {evt.event_id}</span>
                      <span>Run ID: {evt.run_id}</span>
                    </div>
                    <pre className="text-cyan-300/90 whitespace-pre-wrap font-mono text-[10px]">
                      {JSON.stringify(evt.payload, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
